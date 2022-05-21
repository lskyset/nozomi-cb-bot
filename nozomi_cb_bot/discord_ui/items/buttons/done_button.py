import discord

from nozomi_cb_bot import emoji
from nozomi_cb_bot.cb import Boss
from nozomi_cb_bot.discord_ui.modals.done_modal import DoneModal


class DoneButton(discord.ui.Button):
    def __init__(self, boss: Boss):
        self._boss = boss
        super().__init__(
            label="Done",
            style=discord.ButtonStyle.grey,
            emoji=emoji.hit,
            custom_id=f"DoneButton:{self._boss.number}",
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(DoneModal(self._boss))
