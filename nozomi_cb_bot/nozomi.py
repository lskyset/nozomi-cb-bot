import os

import discord
import gspread
from discord.ext import commands
from oauth2client.service_account import ServiceAccountCredentials
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

from . import emoji as e
from .commands.clanbattle import Cb_commands
from .commands.global_commands import Global_commands
from .commands.mod import Mod_commands
from .commands.util import find_clan
from .config import BotConfig
from .db.clan import Clan
from .db.db_helper import create_cb_db
from .db.util import download_db
from .ui import Ui

bot_config = BotConfig()
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(
    command_prefix=bot_config.PREFIX,
    description="List of commands : (Under construction)",
    intents=intents,
    case_insensitive=True,
)
bot.help_command = commands.DefaultHelpCommand(dm_help=True, no_category="Other")
bot.clans = []


gc = None
drive = None
if not bot_config.DISABLE_DRIVE:
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "nozomi-bot-19331373ee16.json", scope
    )
    gc = gspread.authorize(creds)

    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("mycreds.txt")
    drive = GoogleDrive(gauth)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}.\n")
    for cfg_clan_name, cfg_clan_data in bot_config.CLANS.items():
        if cfg_clan_data["ENV"] == bot_config.BOT_ENV and cfg_clan_name != "default":
            channel = bot.get_channel(cfg_clan_data["CHANNEL_ID"])
            await cb_init(channel, cfg_clan_name, cfg_clan_data)


@bot.event
async def on_button_click(i: discord.Interaction, b: discord.ButtonClick):
    await i.defer()
    ctx = await bot.get_context(i.message)
    ctx.author = i.author
    ctx.message.author = i.author
    await ctx.invoke(bot.get_command(b.custom_id), from_button=True)


@bot.event
async def on_message(message):
    clan = find_clan(message, bot.clans)
    if clan:
        clan.log(message)
        if message.author.bot:
            return
        await message.delete(delay=3)
        await bot.process_commands(message)


@bot.event
async def on_command_error(ctx, error):
    react_errors = (commands.CommandNotFound, commands.InvalidEndOfQuotedStringError)
    ignore_errors = commands.CheckFailure
    if isinstance(error, react_errors):
        await ctx.message.add_reaction(e.cross)
    elif isinstance(error, ignore_errors):
        return
    elif bot_config.BOT_ENV > 0:
        raise error


bot.add_cog(Global_commands(bot))
bot.add_cog(Cb_commands(bot))
bot.add_cog(Mod_commands(bot))


async def cb_init(channel, db_name, clan_config):
    if bot_config.BOT_ENV > 0:
        db_name += "_dev"
    path = f"{db_name}.db"
    clan = setup_database(path, db_name, clan_config, channel)
    if clan is None:
        print(f"Failed to initialize clan database for {path}")
    determine_mods(clan, clan_config, channel)
    clan.is_daily_reset = False
    clan.ui = Ui()
    await clan.ui.start(channel, clan)


def setup_database(path, db_name, clan_config, channel):
    clan = None
    if os.path.isfile(path) or (
        not bot_config.DISABLE_DRIVE and download_db(path, drive)
    ):
        msg = f"{db_name}.db has been started."
        print_database_message(msg, channel)
        clan = Clan(db_name, clan_config, drive, gc)
        bot.clans.append(clan)
    else:
        create_cb_db(db_name, channel.guild.id, channel.id)
        clan = Clan(db_name, clan_config, drive, gc)
        bot.clans.append(clan)
        for member in channel.guild.get_role(clan_config["CLAN_ROLE_ID"]).members:
            clan.add_member(member)
        msg = f"{db_name}.db has been created and started."
        print_database_message(msg, channel)
        clan.drive_update()
    return clan


def determine_mods(clan, clan_config, channel):
    mods_members = channel.guild.get_role(clan_config["CLAN_MOD_ROLE_ID"]).members
    for member in mods_members:
        if clan.find_member(member.id):
            clan.mods.append(member.id)


def print_database_message(msg, channel):
    print(f'{msg[:-1]} in "{channel.guild.name}" #{channel.name}.')


def start():
    if not bot_config.DISCORD_TOKEN:
        return
    bot.run(bot_config.DISCORD_TOKEN)
