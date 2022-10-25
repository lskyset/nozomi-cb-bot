from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from functools import reduce
from typing import TYPE_CHECKING

import discord
import pytz

from nozomi_cb_bot.config import CB_DATA, ClanConfig, PricoCbData, jst_time
from nozomi_cb_bot.protocols.database import CbDatabase
from nozomi_cb_bot.response_messages import ErrorMessage, NoticeMessage

if TYPE_CHECKING:
    from nozomi_cb_bot import cb


@dataclass
class Clan:
    config: ClanConfig
    _db: CbDatabase
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

        c = self._db._c
        data = c.execute("SELECT * from cb_data").fetchone()
        if data:
            columns = c.execute("PRAGMA table_info(cb_data)").fetchall()
            for column in columns:
                if data[column[0]] is not None:
                    setattr(self, column[1], data[column[0]])
        self.bosses = self._db.get_all_bosses(self)

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
        self._db.save_clan(self)

    def save(self):
        for member in self.members:
            member._save()
        for boss in self.bosses:
            boss._save()
        self._save()

    def hitting(
        self, member: cb.Member, boss: cb.Boss, *args
    ) -> ErrorMessage | NoticeMessage:
        if boss.wave - self.wave > 1 or boss.tier != self.tier:
            return ErrorMessage.BOSS_WAVE_AHEAD
        if member.hitting_boss_number:
            return ErrorMessage.MEMBER_ALREADY_HITTING
        if boss.hitting_member_id and boss.hitting_member_id != member.discord_id:
            return ErrorMessage.BOSS_ALREADY_HIT
        if self.skip_line != 1:
            fiq_iq = boss.get_first_in_queue_id()
            if fiq_iq and member.discord_id != fiq_iq:
                return ErrorMessage.NO_PRIO
        member._of_status = "of" in args or member.of_status
        boss.hitting_member_id = member.discord_id
        member._hitting_boss_number = boss.number
        self.dequeue(member, boss)
        boss.queue_timeout = None
        member._save()
        boss._save()
        return NoticeMessage.EMPTY

    def syncing(
        self, member: cb.Member, sync_member: cb.Member, boss, *args
    ) -> ErrorMessage | NoticeMessage:
        if not member.hitting_boss_number:
            result = self.hitting(member, boss, *args)
            if isinstance(result, ErrorMessage):
                return result
        if sync_member.hitting_boss_number:
            return ErrorMessage.SYNC_ALREADY_HITTING
        if boss.syncing_member_id is not None:
            old_sync_member = self.find_member(boss.syncing_member_id)
            if old_sync_member is not None:
                old_sync_member._hitting_boss_number = None
                old_sync_member._save()
        boss.syncing_member_id = sync_member.discord_id
        sync_member._hitting_boss_number = boss.number
        self.dequeue(sync_member, boss)
        boss.queue_timeout = None
        sync_member._save()
        boss._save()
        return NoticeMessage.SYNC

    def cancel_hit(self, member: cb.Member) -> cb.Boss | None:
        boss = self.find_boss(boss_number=member.hitting_boss_number)
        if not boss:
            return None
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

    def done(self, member: cb.Member, *args) -> ErrorMessage | NoticeMessage:
        ret = NoticeMessage.EMPTY
        if member is not None:
            boss = self.find_boss(boss_number=member.hitting_boss_number)
        if member is not None and boss is not None:
            if not args:
                return ErrorMessage.NO_ARGS
            parsedDmg = re.match(
                r"^([0-9]+\.?[0-9]*([mk])?)", args[0].replace(",", ".")
            )
            if parsedDmg is None:
                return ErrorMessage.NO_DAMAGE
            dmg = min(replace_num(parsedDmg.group(0)), boss.hp)
            if not dmg:
                return ErrorMessage.NO_DAMAGE
            member._of_status = "of" in args or member.of_status
            if not member.of_status and member.remaining_hits <= 0:
                member.of_status = True
                ret = NoticeMessage.NO_HITS_LEFT
            of = member._of_status
            boss_is_dead = member.deal_damage(dmg, boss)
            self.add_damage_log(boss, member, dmg, of, boss_is_dead)
            setattr(
                self,
                f"d{self.day}_dmg",
                getattr(self, f"d{self.day}_dmg") + dmg,
            )
            self.save()
            if (
                boss.hitting_member_id is None
            ):  # if no hitter confirmed within recieve damage
                boss.queue_timeout = jst_time(minutes=self.timeout_minutes)
            return ret
        else:
            if member is not None:
                return ErrorMessage.NOT_CLAIMED

    def queue(self, member: cb.Member, boss: cb.Boss, *args) -> ErrorMessage | None:
        if member.hitting_boss_number == boss.number:
            return ErrorMessage.QUEUE_ALREADY_HITTING

        c = self._db._c
        already_in_queue = c.execute(
            f"SELECT * from queue WHERE boss_number = {boss.number} AND member_id = {member.discord_id}"
        ).fetchone()
        if already_in_queue:
            return ErrorMessage.ALREADY_QUEUED

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
        self._db._conn.commit()
        return None

    def check_queue(self, boss: cb.Boss):
        if boss.queue_timeout and (
            (boss.queue_timeout - jst_time()).total_seconds() <= 0
        ):
            first_in_queue_member_id = boss.get_first_in_queue_id()
            fiq_member = self.find_member(first_in_queue_member_id)
            if fiq_member is not None:
                self.dequeue(fiq_member, boss)

    def dequeue(self, member: cb.Member, boss: cb.Boss) -> ErrorMessage | None:
        c = self._db._c
        c.execute(
            f"DELETE FROM queue WHERE boss_number = {boss.number} AND member_id = {member.discord_id}"
        )
        self._db._conn.commit()
        fiq_id = boss.get_first_in_queue_id()
        if fiq_id and fiq_id == member.discord_id:
            boss.queue_timeout = jst_time(minutes=self.timeout_minutes)
        return None

    def init_members(self, members: list[discord.Member]) -> None:
        for member in members:
            member_from_db = self._db.get_member(self, member)
            if member_from_db is None:
                self.add_member(member)
            else:
                self.members.append(member_from_db)

    def add_member(self, member: discord.Member) -> None:
        if self.find_member(member.id) is None:
            self.members.append(self._db.add_member(self, member))

    def add_members(self, members: list[discord.Member]) -> None:
        new_members = [
            new_member
            for new_member in members
            if self.find_member(new_member.id) is None
        ]
        self.members += self._db.add_members(self, new_members)

    def find_member(self, member_id: int | None) -> cb.Member | None:
        if member_id is None:
            return None
        for member in self.members:
            if member.discord_id == member_id:
                return member
        return None

    def find_boss(
        self, boss_number: int | None = None, message_id: int | None = None
    ) -> cb.Boss | None:
        for boss in self.bosses:
            if (message_id is not None and boss._message_id == message_id) or (
                boss_number is not None and boss.number == boss_number
            ):
                return boss
        return None

    def add_damage_log(
        self, boss: cb.Boss, member: cb.Member, damage: int, overflow=False, dead=False
    ):
        c = self._db._c
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
        c = self._db._c
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
        boss = self.find_boss(boss_number=hit["boss_number"])

        boss_hits = boss.get_damage_log()
        p_boss_hits = boss.get_damage_log(wave_offset=-1)

        if boss_hits:
            if hit == boss_hits[-1]:
                c = self._db._c
                c.execute(
                    f'DELETE FROM damage_log WHERE timestamp = {hit["timestamp"]} AND member_id = {hit["member_id"]}'
                )
                self._db._conn.commit()
                boss._hp += hit["damage"]
                member.remaining_hits += (hit["overflow"] + 1) % 2
                member.of_number += hit["overflow"]
                member.of_status = bool(hit["overflow"])
                member._save()
                boss._save()
                return boss
        elif p_boss_hits:
            if hit == p_boss_hits[-1]:
                c = self._db._c
                c.execute(
                    f'DELETE FROM damage_log WHERE timestamp = {hit["timestamp"]} AND member_id = {hit["member_id"]}'
                )
                self._db._conn.commit()
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
        prev_day = self.day - 1
        if prev_day < 1 or prev_day > 5:
            return
        print(f"\nDay {prev_day} hits :")
        c = self._db._c
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
        self.save()

    def log(self, message):
        if message.content:
            jst = message.created_at.astimezone(pytz.timezone("Japan")).strftime(
                "%m/%d/%Y %H:%M:%S"
            )
            log = (jst, message.author.display_name, message.clean_content)
            c = self._db._c
            c.execute("INSERT INTO chat_log VALUES (?,?,?)", log)
            self._db._conn.commit()


def replace_num(num):
    if num[-1] in ["k", "m"]:
        return int(float(num[:-1]) * 10 ** (3 + 3 * (num[-1] == "m")))
    return int(float(num))
