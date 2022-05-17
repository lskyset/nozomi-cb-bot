from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field
from functools import reduce
from typing import TYPE_CHECKING

import discord
import pytz

from nozomi_cb_bot import emoji
from nozomi_cb_bot.config import CB_DATA, BotConfig, ClanConfig, PricoCbData, jst_time
from nozomi_cb_bot.db.util import replace_num
from nozomi_cb_bot.protocols.database import CbDatabase

if TYPE_CHECKING:
    from nozomi_cb_bot import cb


@dataclass
class Clan:
    config: ClanConfig
    db: CbDatabase
    cb_data: PricoCbData
    bosses: list[cb.Boss] = field(default_factory=list)
    members: list[cb.Member] = field(default_factory=list)
    overview_message_id: int | None = None
    _overview_message: discord.Message | None = None
    d1_dmg: int = 0
    d2_dmg: int = 0
    d3_dmg: int = 0
    d4_dmg: int = 0
    d5_dmg: int = 0

    def __post_init__(self):
        self.skip_line = 0
        self.timeout_minutes = 0

        # if not bot_config.DISABLE_DRIVE and self.google_drive_sheet:
        #     self.gs_sheet = gc.open_by_key(self.google_drive_sheet["SHEET_KEY"])
        #     self.gs_db = self.gs_sheet.worksheet(
        #         self.google_drive_sheet["DATA_WORKSHEET_NAME"]
        #     )
        #     self.gs_chat_log = self.gs_sheet.worksheet(
        #         self.google_drive_sheet["CHAT_LOG_WORKSHEET_NAME"]
        #     )
        self.drive_loading = False

        c = self.db._c
        data = c.execute("SELECT * from cb_data").fetchone()
        if data:
            columns = c.execute("PRAGMA table_info(cb_data)").fetchall()
            for column in columns:
                if data[column[0]] is not None:
                    setattr(self, column[1], data[column[0]])
        self.bosses = self.db.get_bosses(self)

    @property
    def overview_message(self) -> discord.Message | None:
        return self._overview_message

    @overview_message.setter
    def overview_message(self, message: discord.Message) -> None:
        self._overview_message = message
        self.overview_message_id = message.id
        self._save()

    @property
    def tier(self) -> int:
        return min([boss.tier for boss in self.bosses])

    @property
    def wave(self) -> int:
        return min([boss.wave for boss in self.bosses])

    @property
    def day(self) -> int:
        return math.ceil(
            (jst_time() - CB_DATA.START_DATE).total_seconds() / 60 / 60 / 24
        )

    @property
    def hits_left(self) -> int:
        return reduce(
            lambda a, b: a + b, [member.remaining_hits for member in self.members]
        )

    def _save(self):
        self.db.save_clan(self)

    def full_update(self):
        for member in self.members:
            member._save()
        for boss in self.bosses:
            boss._save()
        self._save()

    def drive_update(self):
        while self.drive_loading:
            time.sleep(1)
        self.drive_loading = True
        self.full_update()
        # if not bot_config.DISABLE_DRIVE:
        #     update_db(self.drive, self)
        self.drive_loading = False

    async def hitting(self, member_id: int, message: discord.PartialMessage, *args):
        member = self.find_member(member_id)
        boss = self.find_boss(message.id)
        if not (member and boss):
            return False
        if boss.wave - self.wave > 1 or boss.tier != self.tier:
            await message.channel.send(
                f"You can't hit B{boss.number} because it's wave or tier is too far ahead {member.discord_member.mention}",
                delete_after=7,
            )
            return False
        if member.hitting_boss_number:
            await message.channel.send(
                f"You are already hitting B{member.hitting_boss_number} {member.discord_member.mention}",
                delete_after=5,
            )
            return False
        if boss.hitting_member_id and boss.hitting_member_id != member.discord_id:
            await message.channel.send(
                f"Someone is already hitting B{boss.number} {member.discord_member.mention}",
                delete_after=5,
            )
            return False
        if self.skip_line != 1:
            fiq_iq = boss.get_first_in_queue_id()
            if fiq_iq and member.discord_id != fiq_iq:
                await message.channel.send(
                    f"You don't have priority to hit this boss {member.discord_member.mention}",
                    delete_after=5,
                )
                return False
        member._of_status = "of" in args or member.of_status
        boss.hitting_member_id = member.discord_id
        member._hitting_boss_number = boss.number
        self.dequeue(member.discord_id, message)
        boss.queue_timeout = None
        member._save()
        boss._save()
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
                f"{sync_member.name} is already hitting B{sync_member.hitting_boss_number} {member.discord_member.mention}",
                delete_after=7,
            )
            return False
        if boss.syncing_member_id is not None:
            old_sync_member = self.find_member(boss.syncing_member_id)
            if old_sync_member is not None:
                old_sync_member._hitting_boss_number = 0
                old_sync_member._save()
        boss.syncing_member_id = sync_member.discord_id
        sync_member._hitting_boss_number = boss.number
        self.dequeue(sync_member.discord_id, message)
        boss.queue_timeout = None
        sync_member._save()
        boss._save()
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
                    sync_member._hitting_boss_number = 0
                    sync_member._save()
                boss.syncing_member_id = 0
            elif boss.syncing_member_id == member.discord_id:
                boss.syncing_member_id = 0
            member._hitting_boss_number = 0
            if boss.get_first_in_queue_id():
                boss.queue_timeout = jst_time(minutes=self.timeout_minutes)
            member._save()
            boss._save()
            return boss

    async def done(self, member_id: int, message, *args):
        member = self.find_member(member_id)
        if member is not None:
            boss = self.find_boss(member.hitting_boss_number)
        if member is not None and boss is not None:
            if args:
                parsedDmg = re.match(
                    r"^([0-9]+\.?[0-9]*([mk])?)", args[0].replace(",", ".")
                )
                if parsedDmg is None:
                    return False
                dmg = min(replace_num(parsedDmg.group(0)), boss.hp)
                if dmg:
                    await message.add_reaction(emoji.ok)
                    member._of_status = "of" in args or member.of_status
                    if not member.of_status and member.remaining_hits <= 0:
                        await message.channel.send(
                            f"You don't have any hits left {member.discord_member.mention}\nYour hit was counted as Overflow",
                            delete_after=7,
                        )
                        member.of_status = True
                    of = member._of_status
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
                        boss.queue_timeout = jst_time(minutes=self.timeout_minutes)
                else:
                    await message.reply(
                        f"Damages not found {member.discord_member.mention}\nUse `{BotConfig.PREFIX}done <damage dealt>` to register your hit.\nNumbers ending with K and M are also supported",
                        delete_after=7,
                    )
            else:
                await message.reply(
                    f"Argument not found {member.discord_member.mention}\nUse `{BotConfig.PREFIX}done <damage dealt>` to register your hit.\nNumbers ending with K and M are also supported",
                    delete_after=7,
                )
        else:
            if member is not None:
                await message.channel.send(
                    f"You must claim a hit before registering damages {member.discord_member.mention}\nFor example use `{BotConfig.PREFIX}h b1` to claim a hit on b1.",
                    delete_after=7,
                )

    async def queue(self, member_id: int, message, *args):
        member = self.find_member(member_id)
        boss = self.find_boss(message.id)
        if not (member and boss):
            return
        if member.hitting_boss_number == boss.number:
            return await message.channel.send(
                f"You can't queue a boss you are hitting {member.discord_member.mention}",
                delete_after=7,
            )

        c = self.db._c
        already_in_queue = c.execute(
            f"SELECT * from queue WHERE boss_number = {boss.number} AND member_id = {member.discord_id}"
        ).fetchone()
        if already_in_queue:
            return await message.channel.send(
                f"You are already in the queue {member.discord_member.mention}",
                delete_after=7,
            )

        if "of" in args:
            member.of_status = True
            member._save()

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
            boss.queue_timeout = jst_time(minutes=self.timeout_minutes)
        data = (
            boss.number,
            member.discord_id,
            member.name,
            False,
            note,
            int(jst_time().timestamp()),
            queue_wave,
        )
        c.execute("INSERT INTO queue VALUES (?,?,?,?,?,?,?)", data)
        self.db._conn.commit()

    def check_queue(self, message):
        boss = self.find_boss(message.id)
        if not boss:
            return
        if boss.queue_timeout and (
            (boss.queue_timeout - jst_time()).total_seconds() <= 0
        ):
            first_in_queue_id = boss.get_first_in_queue_id()
            self.dequeue(first_in_queue_id, message)

    def dequeue(self, member_id: int, message):
        member = self.find_member(member_id)
        boss = self.find_boss(message.id)
        if not (member and boss):
            return
        c = self.db._c
        c.execute(
            f"DELETE FROM queue WHERE boss_number = {boss.number} AND member_id = {member.discord_id}"
        )
        self.db._conn.commit()
        fiq_id = boss.get_first_in_queue_id()
        if fiq_id and fiq_id == member_id:
            boss.queue_timeout = jst_time(minutes=self.timeout_minutes)

    def add_member(self, member):
        c = self.db._c
        data = (member.id, member.display_name)
        c.execute(
            "INSERT INTO members_data VALUES (?,?,3, 0, 0, 0, 0, 0, 0, 0, False, 0, 0)",
            data,
        )
        c.execute(
            "INSERT INTO missed_hits_data VALUES (?,?,0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)",
            data,
        )
        self.members.append(cb.Member(member.id, self.db._conn))
        self.db._conn.commit()

    def add_members(self, members: list[discord.Member]):
        self.members = self.db.get_members(self, members)

    def find_member(self, member_id: int | None) -> cb.Member | None:
        if member_id is None:
            return None
        for member in self.members:
            if member.discord_id == member_id:
                return member
        return None

    def find_boss(self, message_id_or_boss_number: int) -> cb.Boss | None:
        for boss in self.bosses:
            if (
                boss._message_id == message_id_or_boss_number
                or boss.number == message_id_or_boss_number
            ):
                return boss
        return None

    def add_damage_log(
        self, boss: cb.Boss, member: cb.Member, damage: int, overflow=False, dead=False
    ):
        c = self.db._c
        data = (
            boss.number,
            boss.wave - 1 * dead,
            member.discord_id,
            member.name,
            damage,
            overflow,
            dead,
            int(jst_time().timestamp()),
        )
        c.execute("INSERT INTO damage_log VALUES (?,?,?,?,?,?,?,?)", data)

    def find_last_damage_log(self, member_id: int):
        c = self.db._c
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

    async def undo(self, message):
        member = self.find_member(message.author.id)
        hit = self.find_last_damage_log(member.discord_id)
        if not hit:
            return None
        boss = self.find_boss(hit["boss_number"])

        boss_hits = boss.get_damage_log()
        p_boss_hits = boss.get_damage_log(wave_offset=-1)

        if boss_hits:
            if hit == boss_hits[-1]:
                c = self.db._c
                c.execute(
                    f'DELETE FROM damage_log WHERE timestamp = {hit["timestamp"]} AND member_id = {hit["member_id"]}'
                )
                self.db._conn.commit()
                boss.hp += hit["damage"]
                member.remaining_hits += (hit["overflow"] + 1) % 2
                member.of_number += hit["overflow"]
                member.of_status = bool(hit["overflow"])
                member._save()
                boss._save()
                return boss
        elif p_boss_hits:
            if hit == p_boss_hits[-1]:
                c = self.db._c
                c.execute(
                    f'DELETE FROM damage_log WHERE timestamp = {hit["timestamp"]} AND member_id = {hit["member_id"]}'
                )
                self.db._conn.commit()
                boss._hp = hit["damage"]
                boss._wave -= 1
                member.remaining_hits += (hit["overflow"] + 1) % 2
                member._of_number += hit["overflow"]
                setattr(
                    member,
                    f"_b{boss.number}_hits",
                    getattr(member, f"_b{boss.number}_hits") - 1,
                )
                member._save()
                boss._save()
                return boss
        await message.reply(
            f"You can only undo your last hit if it's the most recent hit on a boss {member.discord_member.mention}"
        )
        return None

    def daily_reset(self):
        self.day = math.ceil(
            (jst_time() - CB_DATA.START_DATE).total_seconds() / 60 / 60 / 24
        )
        prev_day = self.day - 1
        if prev_day < 1 or prev_day > 5:
            return
        print(f"\nDay {prev_day} hits :")
        c = self.db._c
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
            member._save()
        self.drive_update()

    def log(self, message):
        if message.content:
            jst = message.created_at.astimezone(pytz.timezone("Japan")).strftime(
                "%m/%d/%Y %H:%M:%S"
            )
            log = (jst, message.author.display_name, message.clean_content)
            c = self.db._c
            c.execute("INSERT INTO chat_log VALUES (?,?,?)", log)
            self.db._conn.commit()
