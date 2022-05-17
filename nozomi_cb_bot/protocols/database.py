from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import discord

if TYPE_CHECKING:
    from nozomi_cb_bot import cb


class CbDatabase(Protocol):
    def connect(self, path: str | None = None):
        ...

    def save_clan(self, clan: cb.Clan) -> None:
        ...

    def get_bosses(self) -> list[cb.Boss]:
        ...

    def save_boss(self, boss: cb.Boss) -> None:
        ...

    def save_bosses(self, bosses: list[cb.Boss]) -> None:
        ...

    def get_member(self, member: cb.Member) -> cb.Member:
        ...

    def get_members(
        self, clan: cb.Clan, members: list[discord.Member]
    ) -> list[cb.Member]:
        ...
