import discord

from nozomi_cb_bot import emoji
from nozomi_cb_bot.cb import Boss
from nozomi_cb_bot.discord_ui.utils import proxy_command


class DeadButton(discord.ui.Button):
    def __init__(self, boss: Boss):
        self._boss = boss
        super().__init__(
            label="Dead",
            style=discord.ButtonStyle.grey,
            emoji=emoji.dead,
            custom_id=f"DeadButton:{self._boss.number}",
        )

    async def callback(self, interaction: discord.Interaction):
        await proxy_command(interaction, "!dead")
