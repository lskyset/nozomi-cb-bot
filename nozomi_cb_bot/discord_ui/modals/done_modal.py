import discord

from nozomi_cb_bot.cb.boss import Boss
from nozomi_cb_bot.discord_ui.items.inputs import DoneInput
from nozomi_cb_bot.discord_ui.utils import proxy_command


class DoneModal(discord.ui.Modal):
    def __init__(self, boss: Boss):
        self._boss = boss

        super().__init__(
            title=f"Damage registration for B{self._boss.number}",
            timeout=None,
            custom_id=f"DoneModal:{self._boss.number}",
        )
        self.input = DoneInput(boss)
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await proxy_command(interaction, f"!d {self.input.value}")
