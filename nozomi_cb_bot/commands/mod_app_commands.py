import discord
from discord import app_commands
from discord.ext import commands

from nozomi_cb_bot.nozomi import Nozomi
from nozomi_cb_bot.utils.command_utils import proxy_imp_command


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


async def setup(bot: Nozomi):
    await bot.add_cog(ModAppCommands(bot))
