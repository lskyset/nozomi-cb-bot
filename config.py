import pytz
import datetime
import json
import os
import urllib.request
import requests
import sqlite3

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
host = 'prd-priconne-redive.akamaized.net'
manifest_path = '/dl/Resources/%s/Jpn/AssetBundles/Windows/manifest/%s_assetmanifest'
bundles_path = '/dl/pool/AssetBundles'


def jst_time(minutes=0, seconds=0):
    utc_now = datetime.datetime.now(tz=pytz.timezone('UTC'))
    jst_now = utc_now.astimezone(pytz.timezone('Japan'))
    return jst_now + datetime.timedelta(minutes=minutes, seconds=seconds)


def get_prico_version():
    default_ver = 10031020
    max_test_amount = 20
    test_multiplier = 10
    if ENV:
        max_test_amount = 5

    print('Checking for updates...')
    ver = default_ver
    i = 0
    while i < max_test_amount:
        guess = ver + i * test_multiplier
        url = f'http://{host}{manifest_path % (guess, "manifest")}'
        response = requests.get(url)
        if response.status_code == 200:
            ver = guess
            i = 0
        i += 1
    return ver


def get_prico_db(version):
    # get masterdata.db
    urllib.request.urlretrieve(f'http://{host}{manifest_path % (version, "masterdata")}', f'masterdata_{version}.txt')
    cdb_path = f'master_{version}.cdb'
    with open(f'masterdata_{version}.txt') as fd:
        hash_ = fd.readline().split(',')[1]
        urllib.request.urlretrieve(f'http://{host}{bundles_path}/{hash_[:2]}/{hash_}', cdb_path)
    os.popen(f'Coneshell_call.exe -cdb  {cdb_path} master.db').close()
    os.remove(f'masterdata_{version}.txt')
    os.remove(f'master_{version}.cdb')


def get_tier_treshold(cb_id: int):
    conn = sqlite3.connect('master.db')
    c = conn.cursor()
    data = c.execute(f'SELECT phase from clan_battle_2_map_data where clan_battle_id={cb_id}').fetchall()
    tier_threshold = []
    for tier, in set(data):
        threshold, = c.execute(f'SELECT lap_num_from from clan_battle_2_map_data where clan_battle_id={cb_id} and phase={tier}').fetchall()[0]
        tier_threshold.append(threshold)
    tier_threshold.sort()
    return tier_threshold


def get_boss_data(cb_id: int, tier_threshold: list):
    conn = sqlite3.connect('master.db')
    c = conn.cursor()
    boss_data = {}
    for lap_num in tier_threshold:
        phase, *tier_data = c.execute(f'SELECT phase, wave_group_id_1, wave_group_id_2, wave_group_id_3, wave_group_id_4, wave_group_id_5  from clan_battle_2_map_data where clan_battle_id={cb_id} and lap_num_from={lap_num}').fetchone()
        boss_data[f't{phase}'] = []
        boss_num = 1
        for wave_id in tier_data:
            boss_dict = {}
            boss_id, = c.execute(f'SELECT enemy_id_1 from wave_group_data where wave_group_id = {wave_id}').fetchone()
            unit_id, name, hp = c.execute(f'SELECT unit_id, name, hp from enemy_parameter where enemy_id = {boss_id}').fetchone()
            boss_dict['name'] = name
            boss_dict['number'] = boss_num
            boss_dict['wave'] = 1
            boss_dict['img'] = f'https://redive.estertion.win/icon/unit/{unit_id}.webp'
            boss_dict['hp'] = hp
            boss_dict['max_hp'] = hp
            boss_data[f't{phase}'].append(boss_dict)
            boss_num += 1
    return boss_data


def get_prico_db_data():
    conn = sqlite3.connect('master.db')
    c = conn.cursor()
    data = {}
    data['cb_id'], data['cb_start_date'], data['cb_end_date'] = c.execute('SELECT clan_battle_id, start_time, end_time from clan_battle_period').fetchall()[-1]
    data['tier_threshold'] = get_tier_treshold(data['cb_id'])
    data['boss_data'] = get_boss_data(data['cb_id'], data['tier_threshold'])
    return data


def get_cb_data():
    version = get_prico_version()
    if os.path.isfile(f'cache_{version}.json'):
        print(f'Version {version} is already up to date\n')
        with open(f'cache_{version}.json', 'r') as fd:
            data = json.load(fd)
    else:
        print(f'Found new version {version}, updating database...')
        get_prico_db(version)
        data = get_prico_db_data()
        with open(f'cache_{version}.json', 'w') as fd:
            fd.write(json.dumps(data, indent=4))
        print('Updating Done\n')
    return data


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
data = get_cb_data()
tier_threshold = data['tier_threshold']
full_boss_data = data['boss_data']
boss_data = full_boss_data['t1']
for boss in boss_data:
    boss['max_hp'] = [boss['max_hp']]
    for i in range(1, 5):
        boss['max_hp'].append(full_boss_data[f't{i+1}'][boss['number'] - 1]['max_hp'])

if ENV:
    boss_data = boss_data[:5]  # number of bosses to load from 1 to 5 (used for faster startup)
    cb_start_date = jst_time()
    cb_end_date = cb_start_date + datetime.timedelta(minutes=(60 * 24 * 4 + 60 * 19 - 1))
else:
    cb_start_date = data['cb_start_date']
    cb_end_date = data['cb_end_date']
    tz = pytz.timezone('Japan')
    cb_start_date = datetime.datetime.strptime(cb_start_date, '%Y/%m/%d %H:%M').replace(tzinfo=tz)
    cb_end_date = datetime.datetime.strptime(cb_end_date, '%Y/%m/%d %H:%M').replace(tzinfo=tz)
