import discord

from nozomi_cb_bot.cb.boss import Boss
from nozomi_cb_bot.discord_ui.items.buttons import (
    HitButton,
    OverviewJumpButton,
    QueueButton,
)


class BossView(discord.ui.View):
    def __init__(self, boss: Boss):
        super().__init__(timeout=None)
        self.add_item(HitButton(boss))
        self.add_item(QueueButton(boss))
        self.add_item(OverviewJumpButton(boss.clan))
