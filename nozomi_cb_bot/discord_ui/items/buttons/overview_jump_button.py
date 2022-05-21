import discord

from nozomi_cb_bot.cb import Clan


class OverviewJumpButton(discord.ui.Button):
    def __init__(self, clan: Clan):
        url = None
        if clan.overview_message is not None:
            url = clan.overview_message.jump_url
        super().__init__(
            label="Overview",
            url=url,
        )
