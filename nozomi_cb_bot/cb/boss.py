from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import discord

from nozomi_cb_bot.config import PricoCbData
from nozomi_cb_bot.protocols.database import CbDatabase

if TYPE_CHECKING:
    from nozomi_cb_bot import cb


@dataclass
class Boss:
    _number: int
    _wave: int
    _hp: int
    _message_id: int | None
    _hitting_member_id: int | None
    _syncing_member_id: int | None
    _cb_data: PricoCbData
    _db: CbDatabase
    clan: cb.Clan

    def __post_init__(self):
        self._queue_timeout: datetime | None = (
            None  # cfg.jst_time(minutes=clan.timeout_minutes)
        )
        self._message: discord.Message | None = None

    @property
    def number(self) -> int:
        return self._number

    @property
    def wave(self) -> int:
        return self._wave

    @property
    def hp(self) -> int:
        return self._hp

    @property
    def message_id(self) -> int | None:
        return self._message_id

    @message_id.setter
    def message_id(self, message_id: int) -> None:
        self._message_id = message_id
        self._save()

    @property
    def hitting_member_id(self) -> int | None:
        return self._hitting_member_id

    @hitting_member_id.setter
    def hitting_member_id(self, member_id: int) -> None:
        self._hitting_member_id = member_id
        self._save()

    @property
    def syncing_member_id(self) -> int | None:
        return self._syncing_member_id

    @syncing_member_id.setter
    def syncing_member_id(self, member_id: int) -> None:
        self._syncing_member_id = member_id
        self._save()

    @property
    def tier(self) -> int:
        return 1 + self._cb_data.TIER_THRESHOLD.index(
            max([i for i in self._cb_data.TIER_THRESHOLD if self._wave >= i])
        )

    @property
    def name(self) -> str:
        return self._cb_data.BOSSES_DATA[self._number - 1].NAME

    @property
    def max_hp(self) -> int:
        return self._cb_data.BOSSES_DATA[self._number - 1].MAX_HP_LIST[self.tier - 1]

    @property
    def img_url(self) -> str:
        return self._cb_data.BOSSES_DATA[self._number - 1].IMG_URL

    @property
    def queue_timeout(self) -> datetime | None:
        return self._queue_timeout

    @queue_timeout.setter
    def queue_timeout(self, time: datetime) -> None:
        self._queue_timeout = time

    @property
    def can_hit(self) -> bool:
        return all(
            (
                not self._hitting_member_id,
                self.wave_offset < 2,
                self.tier == self.clan.tier,
            )
        )

    @property
    def hitting_member(self) -> cb.Member | None:
        if self.hitting_member_id is not None:
            return self.clan.find_member(self.hitting_member_id)
        return None

    @property
    def syncing_member(self) -> cb.Member | None:
        if self.syncing_member_id is not None:
            return self.clan.find_member(self.syncing_member_id)
        return None

    @property
    def message(self) -> discord.Message | None:
        return self._message

    @message.setter
    def message(self, message: discord.Message) -> None:
        self._message = message
        self.message_id = message.id

    @property
    def wave_offset(self) -> int:
        return self.wave - self.clan.wave

    def _save(self):
        self._db.save_boss(self)

    def recieve_damage(self, damage: int, member_id: int):
        if self._hitting_member_id == member_id:  # reset hitter
            self._hitting_member_id = 0
        elif self.syncing_member_id == member_id:  # reset syncer
            self.syncing_member_id = 0
        if (
            not self._hitting_member_id
        ) and self.syncing_member_id:  # reset hitter -> syncer becomes hitter
            self._hitting_member_id = self.syncing_member_id
            self._syncing_member_id = 0
        self._hp -= damage
        if self._hp <= 0:
            self.next()
            return True
        self._save()
        return False

    def next(self):
        self._wave += 1
        self._hp = self.max_hp
        self._save()

    def get_damage_log(self, wave_offset=0):
        c = self._db._c
        data = c.execute(
            f"SELECT * from damage_log WHERE boss_number = {self.number} AND boss_wave = {self._wave + wave_offset} ORDER BY timestamp"
        ).fetchall()
        if not data:
            return None
        hits = []
        columns = c.execute("PRAGMA table_info(damage_log)").fetchall()
        for hit in data:
            hit_dict = {}
            for column in columns:
                if hit[column[0]] is not None:
                    hit_dict[column[1]] = hit[column[0]]
            hits.append(hit_dict)
        return hits

    def get_queue(self):
        c = self._db._c
        data = c.execute(
            f"SELECT * from queue WHERE boss_number = {self.number} and wave = {self._wave}"
        ).fetchall()
        data += c.execute(
            f"SELECT * from queue WHERE boss_number = {self.number} and wave < {self._wave}"
        ).fetchall()
        if not data:
            return None
        queue = []
        columns = c.execute("PRAGMA table_info(queue)").fetchall()
        for member in data:
            member_dict = {}
            for column in columns:
                if member[column[0]] is not None:
                    member_dict[column[1]] = member[column[0]]
            queue.append(member_dict)
        return queue

    def get_waiting(self):
        c = self._db._c
        data = c.execute(
            f"SELECT * from queue WHERE boss_number = {self.number} and wave > {self._wave} ORDER BY wave"
        ).fetchall()
        if not data:
            return None
        queue = []
        columns = c.execute("PRAGMA table_info(queue)").fetchall()
        for member in data:
            member_dict = {}
            for column in columns:
                if member[column[0]] is not None:
                    member_dict[column[1]] = member[column[0]]
            queue.append(member_dict)
        return queue

    def get_first_in_queue_id(self):
        queue = self.get_queue()
        if not queue:
            return None
        return int(queue[0]["member_id"])
