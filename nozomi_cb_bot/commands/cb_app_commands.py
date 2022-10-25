import discord
from discord import app_commands
from discord.ext import commands

from nozomi_cb_bot.nozomi import Nozomi
from nozomi_cb_bot.utils.command_utils import proxy_command


class CbAppCommands(commands.Cog, name="CB App Commands"):  # type: ignore
    """CB App Commands are commands that can be used in a channel where a clan battle database has been loaded."""

    def __init__(self, bot: Nozomi):
        self.bot = bot

        @bot.tree.command()
        @app_commands.rename(boss_number="boss")
        @app_commands.describe(boss_number="Start hitting a boss.")
        @app_commands.choices(
            boss_number=[
                app_commands.Choice(name="B1", value=1),
                app_commands.Choice(name="B2", value=2),
                app_commands.Choice(name="B3", value=3),
                app_commands.Choice(name="B4", value=4),
                app_commands.Choice(name="B5", value=5),
            ]
        )
        async def hit(
            interaction: discord.Interaction, boss_number: app_commands.Choice[int]
        ):
            await proxy_command(interaction, f"!h b{boss_number.value}")

        @bot.tree.command()
        @app_commands.rename(boss_number="boss")
        @app_commands.describe(boss_number="Start hitting a boss.")
        @app_commands.choices(
            boss_number=[
                app_commands.Choice(name="B1", value=1),
                app_commands.Choice(name="B2", value=2),
                app_commands.Choice(name="B3", value=3),
                app_commands.Choice(name="B4", value=4),
                app_commands.Choice(name="B5", value=5),
            ]
        )
        async def queue(
            interaction: discord.Interaction, boss_number: app_commands.Choice[int]
        ):
            await proxy_command(interaction, f"!q b{boss_number.value}")


async def setup(bot: Nozomi):
    await bot.add_cog(CbAppCommands(bot))
