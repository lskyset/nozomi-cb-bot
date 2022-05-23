from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import discord

from nozomi_cb_bot.config import PricoCbData
from nozomi_cb_bot.protocols.database import CbDatabase

if TYPE_CHECKING:
    from nozomi_cb_bot import cb


@dataclass
class Member:
    _discord_id: int
    _name: str
    _remaining_hits: int
    _total_hits: int
    _b1_hits: int
    _b2_hits: int
    _b3_hits: int
    _b4_hits: int
    _b5_hits: int
    _hitting_boss_number: int | None
    _of_status: bool
    _of_number: int
    _missed_hits: int
    _cb_data: PricoCbData
    _db: CbDatabase
    clan: cb.Clan
    _discord_member: discord.Member

    @property
    def discord_id(self) -> int:
        return self._discord_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def remaining_hits(self) -> int:
        return self._remaining_hits

    @remaining_hits.setter
    def remaining_hits(self, number: int) -> None:
        self._remaining_hits = number
        self._save()

    @property
    def total_hits(self) -> int:
        self._total_hits = (
            self._b1_hits
            + self._b2_hits
            + self._b3_hits
            + self._b4_hits
            + self._b5_hits
        )
        return self._total_hits

    @property
    def b1_hits(self) -> int:
        return self._b1_hits

    @property
    def b2_hits(self) -> int:
        return self._b2_hits

    @property
    def b3_hits(self) -> int:
        return self._b3_hits

    @property
    def b4_hits(self) -> int:
        return self._b4_hits

    @property
    def b5_hits(self) -> int:
        return self._b5_hits

    @property
    def hitting_boss_number(self) -> int | None:
        return self._hitting_boss_number

    @hitting_boss_number.setter
    def hitting_boss_number(self, boss_number: int | None) -> None:
        self._hitting_boss_number = boss_number
        self._save()

    @property
    def of_status(self) -> bool:
        return self._of_status

    @of_status.setter
    def of_status(self, status: bool) -> None:
        self._of_status = status
        self._save()

    @property
    def of_number(self) -> int:
        return self._of_number

    @of_number.setter
    def of_number(self, number: int) -> None:
        self._of_number = number
        self._save()

    @property
    def missed_hits(self) -> int:
        return self._missed_hits

    @missed_hits.setter
    def missed_hits(self, number: int) -> None:
        self._missed_hits = number
        self._save()

    @property
    def discord_member(self) -> discord.Member:
        return self._discord_member

    @discord_member.setter
    def discord_member(self, member) -> None:
        self._discord_member = member
        self._discord_id = member.id
        self._name = member.name
        self._save()

    def _save(self):
        self._db.save_member(self)

    def deal_damage(self, damage, boss: cb.Boss):
        boss_is_dead = boss.recieve_damage(damage, self._discord_id)
        setattr(
            self, f"_b{boss.number}_hits", getattr(self, f"_b{boss.number}_hits") + 1
        )
        if self._of_status:
            self._of_number -= 1
            if self._of_number < 0:
                self._of_number = 0
            self._of_status = False
        else:
            self._remaining_hits -= 1
            if boss_is_dead:
                self._of_number += 1
        self._hitting_boss_number = 0
        self._save()
        return boss_is_dead
