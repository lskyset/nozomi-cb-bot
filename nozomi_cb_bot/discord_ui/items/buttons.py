import discord
from discord.ext import commands

from nozomi_cb_bot import emoji
from nozomi_cb_bot.cb import Boss, Clan


class HitButton(discord.ui.Button):
    def __init__(self, boss: Boss):
        self._boss = boss
        super().__init__(
            label="Hit",
            style=discord.ButtonStyle.grey,
            disabled=not boss.can_hit,
            emoji=emoji.hit,
            custom_id=f"HitButton:hit:{boss.number}",
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if message := interaction.message:
            message.author = interaction.user
            message.content = f"!h b{self._boss.number}"
            client: commands.Bot = interaction.client
            await client.process_commands(message)
            await interaction.followup.send(
                f"You are now hitting B{self._boss.number}", ephemeral=True
            )


class QueueButton(discord.ui.Button):
    def __init__(self, boss: Boss):
        super().__init__(
            label="Queue",
            style=discord.ButtonStyle.grey,
            emoji=emoji.queue,
            custom_id=f"QueueButton:queue:{boss.number}",
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("test", ephemeral=True)


class OverviewJumpButton(discord.ui.Button):
    def __init__(self, clan: Clan):
        url = None
        if clan.overview_message is not None:
            url = clan.overview_message.jump_url
        super().__init__(
            label="Overview",
            url=url,
        )


class BossJumpButton(discord.ui.Button):
    def __init__(self, boss: Boss):
        url = None
        if boss.message is not None:
            url = boss.message.jump_url
        super().__init__(
            label=f"B{boss.number}",
            url=url,
        )
