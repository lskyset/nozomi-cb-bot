import discord

from nozomi_cb_bot.cb import Clan
from nozomi_cb_bot.discord_ui.items.buttons import BossJumpButton


class OverviewView(discord.ui.View):
    def __init__(self, clan: Clan):
        super().__init__(timeout=None)
        for boss in clan.bosses:
            self.add_item(BossJumpButton(boss))
