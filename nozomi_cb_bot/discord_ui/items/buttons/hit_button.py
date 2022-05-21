import discord

from nozomi_cb_bot import emoji
from nozomi_cb_bot.cb import Boss
from nozomi_cb_bot.discord_ui.utils import proxy_command


class HitButton(discord.ui.Button):
    def __init__(self, boss: Boss):
        self._boss = boss
        super().__init__(
            label="Hit",
            style=discord.ButtonStyle.grey,
            disabled=not self._boss.can_hit,
            emoji=emoji.hit,
            custom_id=f"HitButton:{self._boss.number}",
        )

    async def callback(self, interaction: discord.Interaction):
        await proxy_command(interaction, f"!h b{self._boss.number}")
