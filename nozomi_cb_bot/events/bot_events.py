import discord
from discord.ext import commands

from nozomi_cb_bot import emoji as e
from nozomi_cb_bot.ui import Ui

# import gspread
# from nozomi_cb_bot.db.util import download_db
# from oauth2client.service_account import ServiceAccountCredentials
# from pydrive.auth import GoogleAuth
# from pydrive.drive import GoogleDrive


# gc = None
# drive = None
# if not bot_config.DISABLE_DRIVE:
#     scope = [
#         "https://spreadsheets.google.com/feeds",
#         "https://www.googleapis.com/auth/drive",
#     ]
#     creds = ServiceAccountCredentials.from_json_keyfile_name(
#         "nozomi-bot-19331373ee16.json", scope
#     )
#     gc = gspread.authorize(creds)

#     gauth = GoogleAuth()
#     gauth.LoadCredentialsFile("mycreds.txt")
#     drive = GoogleDrive(gauth)


def initialize_events(bot: commands.bot) -> None:
    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user}.\n")
        bot.clan_manager.load_clans_from_config()
        for clan in bot.clan_manager.clans:
            if not (channel := bot.get_channel(clan.config.CHANNEL_ID)):
                continue
            for member in channel.guild.get_role(clan.config.CLAN_ROLE_ID).members:
                clan.add_member(member)
            clan.is_daily_reset = False
            clan.ui = Ui()
            print(
                f"Starting {clan.config.name=} in {channel.guild.name=} {channel.name=}..."
            )
            await clan.ui.start(channel, clan)
            print("Done.")
        #         await cb_init(channel, cfg_clan_name, cfg_clan_data, bot)

    @bot.event
    async def on_button_click(i: discord.Interaction, b: discord.ButtonClick):
        await i.defer()
        ctx = await bot.get_context(i.message)
        ctx.author = i.author
        ctx.message.author = i.author
        await ctx.invoke(bot.get_command(b.custom_id), from_button=True)

    @bot.event
    async def on_message(message):
        clan = bot.clan_manager.find_clan_by_id(
            message.channel.guild.id, message.channel.id
        )
        if clan:
            clan.log(message)
            if message.author.bot:
                return
            await message.delete(delay=3)
            await bot.process_commands(message)

    @bot.event
    async def on_command_error(ctx, error):
        react_errors = (
            commands.CommandNotFound,
            commands.InvalidEndOfQuotedStringError,
        )
        ignore_errors = commands.CheckFailure
        if isinstance(error, react_errors):
            await ctx.message.add_reaction(e.cross)
        elif isinstance(error, ignore_errors):
            return
        elif bot.config.BOT_ENV > 0:
            raise error


# def setup_database(path, db_name, clan_config, channel, bot):
#     if os.path.isfile(path) or (
#         not bot_config.DISABLE_DRIVE and download_db(path, drive)
#     ):
#         clan = Clan(db_name, clan_config, drive, gc)
#     else:
#         clan.drive_update()
#     return clan


# def determine_mods(clan, clan_config, channel):
#     mods_members = channel.guild.get_role(clan_config["CLAN_MOD_ROLE_ID"]).members
#     for member in mods_members:
#         if clan.find_member(member.id):
#             clan.mods.append(member.id)
