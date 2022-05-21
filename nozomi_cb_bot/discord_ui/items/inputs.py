import discord

from nozomi_cb_bot.cb import Boss


class DoneInput(discord.ui.TextInput):
    def __init__(self, boss: Boss):
        self._boss = boss
        super().__init__(
            label="Damage",
            style=discord.TextStyle.short,
            placeholder="Enter damage here.",
            custom_id=f"DoneInput:{self._boss.number}",
        )
