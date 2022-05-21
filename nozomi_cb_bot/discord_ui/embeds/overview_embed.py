import discord

from nozomi_cb_bot.cb import Clan
from nozomi_cb_bot.config import TIER_COLOUR


class OverviewEmbed(discord.Embed):
    def __init__(self, clan: Clan):
        self._clan = clan
        super().__init__(title="Overview")
        self.set_author(name=f"Tier {self._clan.tier}: Wave {self._clan.wave}")
        self._add_boss_fileds()
        self.add_field(
            name="Clan info",
            value=f"**Hits done :** {len(self._clan.members) * 3 - self._clan.hits_left} / {len(self._clan.members) * 3}",
        )
        self.colour = discord.Colour.from_rgb(*TIER_COLOUR[self._clan.tier - 1])

    def _add_boss_fileds(self):
        for boss in self._clan.bosses:
            wave_offset = boss.wave - self._clan.wave
            self.add_field(
                name=f"Boss {boss.number} : {boss.name}",
                value=f"**Wave {boss.wave}**{f' (+{wave_offset})' * (wave_offset > 0)} \n"
                + f"**HP :** *{boss.hp  // 10 ** 6}M / {boss.max_hp // 10 ** 6}M*",
            )
