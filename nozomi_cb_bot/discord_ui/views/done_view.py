import discord

from nozomi_cb_bot.cb.boss import Boss

from ..items.buttons.cancel_button import CancelButton
from ..items.buttons.dead_button import DeadButton
from ..items.buttons.done_button import DoneButton


class DoneView(discord.ui.View):
    def __init__(self, boss: Boss):
        super().__init__(timeout=None)
        self.add_item(DoneButton(boss))
        self.add_item(DeadButton(boss))
        self.add_item(CancelButton(boss))
