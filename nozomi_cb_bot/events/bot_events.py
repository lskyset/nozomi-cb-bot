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
