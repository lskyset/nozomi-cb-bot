from typing import cast

import discord
from discord.ext import commands

from nozomi_cb_bot import emoji
from nozomi_cb_bot.config import BotConfig
from nozomi_cb_bot.discord_ui import discord_ui
from nozomi_cb_bot.managers.clan_manager import ClanManager


class Nozomi(commands.Bot):
    def __init__(self) -> None:
        self.config = BotConfig()

        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(
            command_prefix=self.config.PREFIX,
            description="List of commands : ",
            intents=intents,
            help_command=commands.DefaultHelpCommand(dm_help=True, no_category="Other"),
            case_insensitive=True,
        )

        self.clan_manager = ClanManager(self.config.BOT_ENV)

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user}.")
        for clan in self.clan_manager.clans:
            if not (channel := self.get_channel(clan.config.CHANNEL_ID)):
                continue
            channel = cast(discord.TextChannel, channel)
            if clan_role := channel.guild.get_role(clan.config.CLAN_ROLE_ID):
                clan.init_members(clan_role.members)
        await self.start_uis()
        number_of_clans = len(self.clan_manager.clans)
        print(f"{number_of_clans} Clan{'s' * (number_of_clans > 1)} loaded.")

        if self.config.APP_COMMAND_GUILD_ID:
            guild = discord.Object(id=self.config.APP_COMMAND_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

    async def setup_hook(self) -> None:
        await self.load_commands()
        self.clan_manager.load_clans_from_config()

    async def on_message(self, message: discord.Message) -> None:
        if not (message.channel and message.channel.guild):
            return
        clan = self.clan_manager.find_clan_by_id(
            message.channel.guild.id, message.channel.id
        )
        if clan:
            clan.log(message)
            if message.author.bot:
                return
            await message.delete(delay=3)
            await self.process_commands(message)

    async def on_command_error(self, ctx: commands.Context, error) -> None:
        react_errors = (
            commands.CommandNotFound,
            commands.InvalidEndOfQuotedStringError,
        )
        ignore_errors = commands.CheckFailure
        if isinstance(error, react_errors):
            await ctx.message.add_reaction(emoji.cross)
        elif isinstance(error, ignore_errors):
            return
        elif self.config.BOT_ENV > 0:
            raise error
        print(error)

    async def load_commands(self) -> None:
        print("Loading commands.")
        await self.load_extension("nozomi_cb_bot.commands.global_commands")
        # await self.load_extension("nozomi_cb_bot.commands.cb_app_commands")
        await self.load_extension("nozomi_cb_bot.commands.cb_commands")
        await self.load_extension("nozomi_cb_bot.commands.mod_app_commands")
        await self.load_extension("nozomi_cb_bot.commands.mod_commands")

    async def start_uis(self) -> None:
        print("Starting uis.")
        for clan in self.clan_manager.clans:
            if not (channel := self.get_channel(clan.config.CHANNEL_ID)):
                continue
            channel = cast(discord.TextChannel, channel)
            await discord_ui.start_ui(self, channel, clan)

    def run(self):
        if self.config.DISCORD_TOKEN:
            super().run(self.config.DISCORD_TOKEN)
        else:
            print("Discord token not found.")
