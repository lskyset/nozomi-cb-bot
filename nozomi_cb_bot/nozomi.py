import discord
from discord.ext import commands

from nozomi_cb_bot.commands.clanbattle import Cb_commands
from nozomi_cb_bot.commands.global_commands import Global_commands
from nozomi_cb_bot.commands.mod import Mod_commands
from nozomi_cb_bot.config import BotConfig
from nozomi_cb_bot.events.bot_events import initialize_events
from nozomi_cb_bot.managers.clan_manager import ClanManager


class Nozomi(commands.Bot):
    def __init__(self):
        self.config = BotConfig()

        intents = discord.Intents.default()
        intents.members = True
        super().__init__(
            command_prefix=self.config.PREFIX,
            description="List of commands : ",
            intents=intents,
            help_command=commands.DefaultHelpCommand(dm_help=True, no_category="Other"),
            case_insensitive=True,
        )

        self.clan_manager = ClanManager(self.config.BOT_ENV)
        self.add_cog(Global_commands(self))
        self.add_cog(Cb_commands(self))
        self.add_cog(Mod_commands(self))
        initialize_events(self)

    def run(self):
        if self.config.DISCORD_TOKEN:
            super().run(self.config.DISCORD_TOKEN)
        else:
            print("Discord token not found.")
