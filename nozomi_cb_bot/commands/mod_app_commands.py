import discord
from discord import app_commands
from discord.ext import commands

from nozomi_cb_bot.nozomi import Nozomi
from nozomi_cb_bot.utils.command_utils import proxy_command, proxy_imp_command


class ModAppCommands(commands.Cog, name="Mod App Commands"):  # type: ignore
    """Mod App Commands are commands that can only be used by the clan's leader and sub-leaders."""

    def __init__(self, bot: Nozomi):
        self.bot = bot

        @bot.tree.command()
        @app_commands.describe(
            member="Impersonate another member", command="Command to use."
        )
        async def imp(
            interaction: discord.Interaction, member: discord.Member, command: str
        ):
            await proxy_imp_command(interaction, command, member)

        @bot.tree.command()
        @app_commands.describe(
            boss_number="Boss to edit.", hp="Boss' hp.", wave="Boss' wave."
        )
        @app_commands.choices(
            boss_number=[
                app_commands.Choice(name="B1", value=1),
                app_commands.Choice(name="B2", value=2),
                app_commands.Choice(name="B3", value=3),
                app_commands.Choice(name="B4", value=4),
                app_commands.Choice(name="B5", value=5),
            ]
        )
        async def edit(
            interaction: discord.Interaction,
            boss_number: app_commands.Choice[int],
            hp: int,
            wave: int,
        ):
            await proxy_command(interaction, f"!edit {boss_number} {hp} {wave}")


async def setup(bot: Nozomi):
    await bot.add_cog(ModAppCommands(bot))
