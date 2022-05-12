import math
import re
import sqlite3
import time
import typing

import pytz

from .. import config as cfg
from .. import emoji as e
from ..config import CB_DATA, BotConfig
from ..db.boss import Boss
from ..db.member import Member
from .util import replace_num, update_db

# temp
bot_config = BotConfig()
P = bot_config.PREFIX


class Clan:
    def __init__(self, db_name: str, config: dict, drive: typing.Any, gc: typing.Any):
        self.google_drive_sheet = {}  # type: ignore
        self.skip_line = 0
        self.timeout_minutes = 0
        self.overview_message_id = -1
        self.drive = drive
        self.gc = gc

        for key, val in config.items():
            setattr(self, key.lower(), val)
        if not bot_config.DISABLE_DRIVE and self.google_drive_sheet:
            self.gs_sheet = gc.open_by_key(self.google_drive_sheet["SHEET_KEY"])
            self.gs_db = self.gs_sheet.worksheet(
                self.google_drive_sheet["DATA_WORKSHEET_NAME"]
            )
            self.gs_chat_log = self.gs_sheet.worksheet(
                self.google_drive_sheet["CHAT_LOG_WORKSHEET_NAME"]
            )
        self.drive_loading = False
        self.members = []
        self.mods = []  # type: ignore
        self.day = math.ceil(
            (cfg.jst_time() - CB_DATA.START_DATE).total_seconds() / 60 / 60 / 24
        )
        self.bosses = []

        self.conn = sqlite3.connect(db_name + ".db")
        c = self.conn.cursor()
        data = c.execute("SELECT * from cb_data").fetchone()
        if data:
            columns = c.execute("PRAGMA table_info(cb_data)").fetchall()
            for column in columns:
                if data[column[0]] is not None:
                    setattr(self, column[1], data[column[0]])
            for (member_id,) in c.execute(
                "SELECT discord_id from members_data"
            ).fetchall():
                self.members.append(Member(member_id, self.conn))
        for boss_data in CB_DATA.BOSSES_DATA:
            boss = Boss(boss_data, self)
            self.bosses.append(boss)
        self.current_wave = min([boss.wave for boss in self.bosses])
        self.current_tier = min([boss.tier for boss in self.bosses])

    def update(self):
        self.current_wave = min([boss.wave for boss in self.bosses])
        self.current_tier = min([boss.tier for boss in self.bosses])
        c = self.conn.cursor()
        for key, val in self.__dict__.items():
            try:
                c.execute(f"UPDATE cb_data SET {key} = ?", (val,))
            except sqlite3.OperationalError:
                pass
        self.conn.commit()

    def full_update(self):
        for member in self.members:
            member.update()
        for boss in self.bosses:
            boss.update()
        self.update()

    def drive_update(self):
        while self.drive_loading:
            time.sleep(1)
        self.drive_loading = True
        self.full_update()
        if not bot_config.DISABLE_DRIVE:
            update_db(self.drive, self)
        self.drive_loading = False

    async def hitting(self, member_id: int, message, *args):
        member = self.find_member(member_id)
        boss = self.find_boss(message.id)
        if not (member and boss):
            return False
        if boss.wave - self.current_wave > 1 or boss.tier != self.current_tier:
            await message.channel.send(
                f"You can't hit B{boss.number} because it's wave or tier is too far ahead {message.author.mention}",
                delete_after=7,
            )
            return False
        if member.hitting_boss_number:
            await message.channel.send(
                f"You are already hitting B{member.hitting_boss_number} {message.author.mention}",
                delete_after=5,
            )
            return False
        if boss.hitting_member_id and boss.hitting_member_id != member.discord_id:
            await message.channel.send(
                f"Someone is already hitting B{boss.number} {message.author.mention}",
                delete_after=5,
            )
            return False
        if self.skip_line != 1:
            fiq_iq = boss.get_first_in_queue_id()
            if fiq_iq and member.discord_id != fiq_iq:
                await message.channel.send(
                    f"You don't have priority to hit this boss {message.author.mention}",
                    delete_after=5,
                )
                return False
        member.of_status = "of" in args or member.of_status
        boss.hitting_member_id = member.discord_id
        member.hitting_boss_number = boss.number
        self.dequeue(member.discord_id, message)
        boss.queue_timeout = None
        member.update()
        boss.update()
        return True

    async def syncing(self, member_id: int, sync_member_id: int, message, *args):
        member = self.find_member(member_id)
        sync_member = self.find_member(sync_member_id)
        boss = self.find_boss(message.id)
        if not member:
            return False
        if not member.hitting_boss_number:
            if not await self.hitting(member_id, message, *args):
                return False
        if not (sync_member and boss):
            return False
        if sync_member.hitting_boss_number:
            await message.channel.send(
                f"{sync_member.name} is already hitting B{sync_member.hitting_boss_number} {message.author.mention}",
                delete_after=7,
            )
            return False
        if boss.syncing_member_id:
            old_sync_member = self.find_member(boss.syncing_member_id)
            old_sync_member.hitting_boss_number = 0
            old_sync_member.update()
        boss.syncing_member_id = sync_member.discord_id
        sync_member.hitting_boss_number = boss.number
        self.dequeue(sync_member.discord_id, message)
        boss.queue_timeout = None
        sync_member.update()
        boss.update()
        return True

    def cancel_hit(self, member_id: int):
        member = self.find_member(member_id)
        if not member:
            return False
        boss = self.find_boss(member.hitting_boss_number)
        if not boss:
            return False
        if member.hitting_boss_number == boss.number:
            if boss.hitting_member_id == member.discord_id:
                boss.hitting_member_id = 0
                sync_member = self.find_member(boss.syncing_member_id)
                if sync_member:
                    sync_member.hitting_boss_number = 0
                    sync_member.update()
                boss.syncing_member_id = 0
            elif boss.syncing_member_id == member.discord_id:
                boss.syncing_member_id = 0
            member.hitting_boss_number = 0
            if boss.get_first_in_queue_id():
                boss.queue_timeout = cfg.jst_time(minutes=self.timeout_minutes)
            member.update()
            boss.update()
            return boss

    async def done(self, member_id: int, message, *args):
        member = self.find_member(member_id)
        boss = self.find_boss(member.hitting_boss_number)
        if member and boss:
            if args:
                parsedDmg = re.match(
                    r"^([0-9]+\.?[0-9]*([mk])?)", args[0].replace(",", ".")
                )
                if parsedDmg is None:
                    return False
                dmg = min(replace_num(parsedDmg.group(0)), boss.hp)
                if dmg:
                    await message.add_reaction(e.ok)
                    member.of_status = "of" in args or member.of_status
                    if not member.of_status and member.remaining_hits <= 0:
                        await message.channel.send(
                            f"You don't have any hits left {message.author.mention}\nYour hit was counted as Overflow",
                            delete_after=7,
                        )
                        member.of_status = True
                    of = member.of_status
                    boss_is_dead = member.deal_damage(dmg, boss)
                    self.add_damage_log(boss, member, dmg, of, boss_is_dead)
                    setattr(
                        self,
                        f"d{self.day}_dmg",
                        getattr(self, f"d{self.day}_dmg") + dmg,
                    )
                    self.drive_update()
                    if (
                        boss.hitting_member_id == 0
                    ):  # if no hitter confirmed within recieve damage
                        boss.queue_timeout = cfg.jst_time(minutes=self.timeout_minutes)
                else:
                    await message.respond(
                        f"Damages not found {message.author.mention}\nUse `{P}done <damage dealt>` to register your hit.\nNumbers ending with K and M are also supported",
                        delete_after=7,
                    )
            else:
                await message.respond(
                    f"Argument not found {message.author.mention}\nUse `{P}done <damage dealt>` to register your hit.\nNumbers ending with K and M are also supported",
                    delete_after=7,
                )
        else:
            await message.channel.send(
                f"You must claim a hit before registering damages {message.author.mention}\nFor example use `{P}h b1` to claim a hit on b1.",
                delete_after=7,
            )

    async def queue(self, member_id: int, message, *args):
        member = self.find_member(member_id)
        boss = self.find_boss(message.id)
        if not (member and boss):
            return
        if member.hitting_boss_number == boss.number:
            return await message.channel.send(
                f"You can't queue a boss you are hitting {message.author.mention}",
                delete_after=7,
            )

        c = self.conn.cursor()
        already_in_queue = c.execute(
            f"SELECT * from queue WHERE boss_number = {boss.number} AND member_id = {member.discord_id}"
        ).fetchone()
        if already_in_queue:
            return await message.channel.send(
                f"You are already in the queue {message.author.mention}", delete_after=7
            )

        if "of" in args:
            member.of_status = True
            member.update()

        full_arg = " ".join(args)
        note = ""
        parsedNote = re.search(r"\[.*\]", full_arg)
        if parsedNote:
            note = parsedNote.group(0)[1:-1]

        queue_wave = 0
        for arg in args:
            if re.match(r"^w[0-9]*$", arg):
                queue_wave = max(boss.wave + 1, int(arg[1:]))
                break

        if not boss.get_first_in_queue_id():
            boss.queue_timeout = cfg.jst_time(minutes=self.timeout_minutes)
        data = (
            boss.number,
            member.discord_id,
            member.name,
            False,
            note,
            int(cfg.jst_time().timestamp()),
            queue_wave,
        )
        c.execute("INSERT INTO queue VALUES (?,?,?,?,?,?,?)", data)
        self.conn.commit()

    def check_queue(self, message):
        boss = self.find_boss(message.id)
        if not boss:
            return
        if boss.queue_timeout and (
            (boss.queue_timeout - cfg.jst_time()).total_seconds() <= 0
        ):
            first_in_queue_id = boss.get_first_in_queue_id()
            self.dequeue(first_in_queue_id, message)

    def dequeue(self, member_id: int, message):
        member = self.find_member(member_id)
        boss = self.find_boss(message.id)
        if not (member and boss):
            return
        c = self.conn.cursor()
        c.execute(
            f"DELETE FROM queue WHERE boss_number = {boss.number} AND member_id = {member.discord_id}"
        )
        self.conn.commit()
        fiq_id = boss.get_first_in_queue_id()
        if fiq_id and fiq_id == member_id:
            boss.queue_timeout = cfg.jst_time(minutes=self.timeout_minutes)

    def add_member(self, member):
        c = self.conn.cursor()
        data = (member.id, member.display_name)
        c.execute(
            "INSERT INTO members_data VALUES (?,?,3, 0, 0, 0, 0, 0, 0, 0, False, 0, 0)",
            data,
        )
        c.execute(
            "INSERT INTO missed_hits_data VALUES (?,?,0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)",
            data,
        )
        self.members.append(Member(member.id, self.conn))
        self.conn.commit()

    def find_member(self, member_id: int):
        for member in self.members:
            if member.discord_id == member_id:
                return member

    def find_boss(self, message_id_or_boss_number: int):
        for boss in self.bosses:
            if (
                boss.message_id == message_id_or_boss_number
                or boss.number == message_id_or_boss_number
            ):
                return boss

    def add_damage_log(self, boss, member, damage: int, overflow=False, dead=False):
        c = self.conn.cursor()
        data = (
            boss.number,
            boss.wave - 1 * dead,
            member.discord_id,
            member.name,
            damage,
            overflow,
            dead,
            int(cfg.jst_time().timestamp()),
        )
        c.execute("INSERT INTO damage_log VALUES (?,?,?,?,?,?,?,?)", data)

    def find_last_damage_log(self, member_id: int):
        c = self.conn.cursor()
        logs = c.execute(
            f"SELECT * from damage_log WHERE member_id = {member_id} ORDER BY timestamp"
        ).fetchall()
        if not logs:
            return None
        data = logs[-1]
        hit = {}
        columns = c.execute("PRAGMA table_info(damage_log)").fetchall()
        for column in columns:
            if data[column[0]] is not None:
                hit[column[1]] = data[column[0]]
        return hit

    def undo(self, message):
        member = self.find_member(message.author.id)
        hit = self.find_last_damage_log(member.discord_id)
        if not hit:
            return None
        boss = self.find_boss(hit["boss_number"])

        boss_hits = boss.get_damage_log()
        p_boss_hits = boss.get_damage_log(wave_offset=-1)

        if boss_hits:
            if hit == boss_hits[-1]:
                c = self.conn.cursor()
                c.execute(
                    f'DELETE FROM damage_log WHERE timestamp = {hit["timestamp"]} AND member_id = {hit["member_id"]}'
                )
                self.conn.commit()
                boss.hp += hit["damage"]
                member.remaining_hits += (hit["overflow"] + 1) % 2
                member.of_number += hit["overflow"]
                member.of_status = bool(hit["overflow"])
                member.update()
                boss.update()
                return boss
        elif p_boss_hits:
            if hit == p_boss_hits[-1]:
                c = self.conn.cursor()
                c.execute(
                    f'DELETE FROM damage_log WHERE timestamp = {hit["timestamp"]} AND member_id = {hit["member_id"]}'
                )
                self.conn.commit()
                boss.hp = hit["damage"]
                boss.wave -= 1
                boss.tier = 1 + CB_DATA.TIER_THRESHOLD.index(
                    max([i for i in CB_DATA.TIER_THRESHOLD if boss.wave >= i])
                )
                member.remaining_hits += (hit["overflow"] + 1) % 2
                member.of_number += hit["overflow"]
                setattr(
                    member,
                    f"b{boss.number}_hits",
                    getattr(member, f"b{boss.number}_hits") - 1,
                )
                member.total_hits -= 1
                member.update()
                boss.update()
                return boss
        message.respond(
            f"You can only undo your last hit if it's the most recent hit on a boss {message.author.mention}"
        )
        return None

    def daily_reset(self):
        self.day = math.ceil(
            (cfg.jst_time() - CB_DATA.START_DATE).total_seconds() / 60 / 60 / 24
        )
        prev_day = self.day - 1
        if prev_day < 1 or prev_day > 5:
            return
        print(f"\nDay {prev_day} hits :")
        c = self.conn.cursor()
        for member in self.members:
            data = list(
                c.execute(
                    f"select total_missed_hits, total_missed_of, d{prev_day}_missed_hits, d{prev_day}_missed_of from missed_hits_data where discord_id = {member.discord_id}"
                ).fetchone()
            )
            if member.remaining_hits > 0:
                print("{0.name} had {0.remaining_hits} hits left".format(member))
                member.missed_hits += member.remaining_hits
                data[0] += member.remaining_hits
                data[2] = member.remaining_hits
                data[1] += member.of_number
                data[3] = member.of_number
            c.execute(
                f"""UPDATE missed_hits_data
                SET total_missed_hits = {data[0]},
                total_missed_of = {data[1]},
                d{prev_day}_missed_hits = {data[2]},
                d{prev_day}_missed_of = {data[3]}
                WHERE discord_id = {member.discord_id}"""
            )

            member.remaining_hits = 3
            member.of_status = False
            member.of_number = 0
            member.update()
        self.drive_update()

    def log(self, message):
        if message.content:
            jst = message.created_at.astimezone(pytz.timezone("Japan")).strftime(
                "%m/%d/%Y %H:%M:%S"
            )
            log = (jst, message.author.display_name, message.clean_content)
            c = self.conn.cursor()
            c.execute("INSERT INTO chat_log VALUES (?,?,?)", log)
            self.conn.commit()
