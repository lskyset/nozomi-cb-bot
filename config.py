import pytz
import datetime
import json
import os

discord_token_file_name = 'discord_token.txt'
if os.path.isfile(discord_token_file_name):
    with open(discord_token_file_name, 'r') as fd:
        TOKEN = fd.readline()
else:
    print(f'Error: {discord_token_file_name} not found')
    exit()
PREFIX = "!"
ENV = 1
DISABLE_DRIVE = True


def jst_time(minutes=0, seconds=0):
    utc_now = datetime.datetime.now(tz=pytz.timezone('UTC'))
    jst_now = utc_now.astimezone(pytz.timezone('Japan'))
    return jst_now + datetime.timedelta(minutes=minutes, seconds=seconds)


tier_threshold = [1, 4, 11, 31, 41]
boss_data = [
    {
        'name': 'Goblin Great',
        'number': 1,
        'wave': 1,
        'img': 'https://media.discordapp.net/attachments/796797906706497536/824682105832865803/Goblin-great-icon.png',
        'max_hp': [6, 6, 12, 19, 85],
        'hp': 6000000,
    },
    {
        'name': 'Wild Griffon',
        'number': 2,
        'wave': 1,
        'img': 'https://media.discordapp.net/attachments/796797906706497536/803289507515334676/WIld-Griffon.png',
        'max_hp': [8, 8, 14, 20, 90],
        'hp': 8000000,
    },
    {
        'name': 'Basilisk',
        'number': 3,
        'wave': 1,
        'img': 'https://media.discordapp.net/attachments/796797906706497536/824682179430449182/Basilisk.png',
        'max_hp': [10, 10, 17, 23, 95],
        'hp': 10000000,
    },
    {
        'name': 'Mover',
        'number': 4,
        'wave': 1,
        'img': 'https://cdn.discordapp.com/attachments/796797906706497536/868937321444151316/icon_unit_304001.png',
        'max_hp': [12, 12, 19, 25, 100],
        'hp': 12000000,
    },
    {
        'name': 'Orleon',
        'number': 5,
        'wave': 1,
        'img': 'https://media.discordapp.net/attachments/796797906706497536/868937445595574292/icon_unit_302803.png',
        'max_hp': [15, 15, 22, 27, 110],
        'hp': 15000000,
    },
]


if ENV:
    boss_data = boss_data[:1]  # number of bosses to load from 1 to 5 (used for faster startup)
    cb_start_date = jst_time()
    cb_end_date = cb_start_date + datetime.timedelta(minutes=(60 * 24 * 4 + 60 * 19 - 1))
else:
    cb_start_date = '2021/7/26 05:00'
    cb_end_date = '2021/7/30 23:59'
    tz = pytz.timezone('Japan')
    cb_start_date = datetime.datetime.strptime(cb_start_date, '%Y/%m/%d %H:%M').replace(tzinfo=tz)
    cb_end_date = datetime.datetime.strptime(cb_end_date, '%Y/%m/%d %H:%M').replace(tzinfo=tz)


def load_clans(clans_cgf_file_name):
    if os.path.isfile(clans_cgf_file_name):
        with open('clans_config.json', 'r') as clans_cfg:
            clan_dict = json.load(clans_cfg)
            try:
                clan_dict['default']
            except KeyError:
                clan_dict['default'] = {'ENV': ENV, 'GUILD_ID': 0, 'CHANNEL_ID': 0, 'CLAN_ROLE_ID': 0, 'CLAN_MOD_ROLE_ID': 0, 'GOOGLE_DRIVE_SHEET': 0, 'TIMEOUT_MINUTES': 15}
            for name, data in clan_dict.items():
                for key, value in clan_dict['default'].items():
                    try:
                        data[key]
                    except KeyError:
                        data[key] = value
            return clan_dict
    else:
        print(f'{clans_cgf_file_name} not found')
        clan_dict = {'default': {'ENV': ENV, 'GUILD_ID': 0, 'CHANNEL_ID': 0, 'CLAN_ROLE_ID': 0, 'CLAN_MOD_ROLE_ID': 0, 'GOOGLE_DRIVE_SHEET': 0, 'TIMEOUT_MINUTES': 15}}
        with open(clans_cgf_file_name, 'w') as fd:
            fd.write(json.dumps(clan_dict, indent=4))
            print(f'a default {clans_cgf_file_name} was created')
        return clan_dict


CLANS = load_clans('clans_config.json')
