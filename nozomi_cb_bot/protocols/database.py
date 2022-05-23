from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import discord

if TYPE_CHECKING:
    from nozomi_cb_bot import cb


class CbDatabase(Protocol):
    def save_clan(self, clan: cb.Clan) -> None:
        ...

    def get_boss(self, clan: cb.Clan, message: discord.Message) -> cb.Boss:
        ...

    def get_all_bosses(self, clan: cb.Clan) -> list[cb.Boss]:
        ...

    def save_boss(self, boss: cb.Boss) -> None:
        ...

    def save_bosses(self, bosses: list[cb.Boss]) -> None:
        ...

    def add_member(self, clan: cb.Clan, member: discord.Member) -> cb.Member:
        ...

    def add_members(
        self, clan: cb.Clan, members: list[discord.Member]
    ) -> list[cb.Member]:
        ...

    def get_member(self, clan: cb.Clan, member: discord.Member) -> cb.Member:
        ...

    def get_members(
        self, clan: cb.Clan, members: list[discord.Member]
    ) -> list[cb.Member]:
        ...

    def save_member(self, member: cb.Member) -> None:
        ...

    def save_members(self, members: list[cb.Member]) -> None:
        ...
