import discord

from nozomi_cb_bot import emoji
from nozomi_cb_bot.cb import Boss
from nozomi_cb_bot.discord_ui.utils import proxy_command


class QueueButton(discord.ui.Button):
    def __init__(self, boss: Boss):
        self._boss = boss
        super().__init__(
            label="Queue",
            style=discord.ButtonStyle.grey,
            emoji=emoji.queue,
            custom_id=f"QueueButton:{self._boss.number}",
        )

    async def callback(self, interaction: discord.Interaction):
        await proxy_command(interaction, f"!q b{self._boss.number}")
