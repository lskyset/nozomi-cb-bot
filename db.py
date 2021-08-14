import sqlite3
import csv
import math
from operator import itemgetter
from itertools import zip_longest
import re
import time
import os

import gspread
import pytz
from oauth2client.service_account import ServiceAccountCredentials
from pydrive.drive import GoogleDrive
from pydrive.auth import GoogleAuth

import config as cfg
import emoji as e
from config import PREFIXE as P

if not cfg.DISABLE_DRIVE:
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('nozomi-bot-19331373ee16.json', scope)
    gc = gspread.authorize(creds)

    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("mycreds.txt")
    drive = GoogleDrive(gauth)


class Clan():
    def __init__(self, db_name: str, config: dict):
        for key, val in config.items():
            setattr(self, key.lower(), val)
        if not cfg.DISABLE_DRIVE and self.google_drive_sheet:
            self.gs_sheet = gc.open_by_key(self.google_drive_sheet['SHEET_KEY'])
            self.gs_db = self.gs_sheet.worksheet(self.google_drive_sheet['DATA_WORKSHEET_NAME'])
            self.gs_chat_log = self.gs_sheet.worksheet(self.google_drive_sheet['CHAT_LOG_WORKSHEET_NAME'])
            self.drive_loading = False
        self.members = []
        self.mods = []
        self.day = math.ceil((cfg.jst_time() - cfg.cb_start_date).total_seconds() / 60 / 60 / 24)
        self.bosses = []

        self.conn = sqlite3.connect(db_name + '.db')
        c = self.conn.cursor()
        data = c.execute('select * from cb_data').fetchone()
        if data:
            columns = c.execute("PRAGMA table_info(cb_data)").fetchall()
            for column in columns:
                if data[column[0]] is not None:
                    setattr(self, column[1], data[column[0]])
            for (member_id,) in c.execute("select discord_id from members_data").fetchall():
                self.members.append(Member(member_id, self.conn))
        for boss_data in cfg.boss_data:
            boss = Boss(boss_data, self)
            self.bosses.append(boss)
        self.current_wave = min([boss.wave for boss in self.bosses])
        self.current_tier = min([boss.tier for boss in self.bosses])

    def update(self):
        self.current_wave = min([boss.wave for boss in self.bosses])
        self.current_tier = min([boss.tier for boss in self.bosses])
        c = self.conn.cursor()
        for key, val in self.__dict__.items():
            try:
                c.execute(f'UPDATE cb_data SET {key} = {val}')
            except sqlite3.OperationalError:
                pass
        self.conn.commit()

    def full_update(self):
        for member in self.members:
            member.update()
        for boss in self.bosses:
            boss.update()
        self.update()

    def drive_update(self):
        if not cfg.DISABLE_DRIVE:
            while self.drive_loading:
                time.sleep(1)
            self.drive_loading = True
            self.full_update()
            update_db(self)
            self.drive_loading = False

    async def hitting(self, member_id: int, message, *args):
        member = self.find_member(member_id)
        boss = self.find_boss(message.id)
        if not (member and boss):
            return False
        if boss.wave - self.current_wave > 1 or boss.tier != self.current_tier:
            await message.channel.send(f"You can't hit B{boss.number} because it's wave or tier is too far ahead {message.author.mention}", delete_after=7)
            return False
        if member.hitting_boss_number:
            await message.channel.send(f'You are already hitting B{member.hitting_boss_number} {message.author.mention}', delete_after=5)
            return False
        if boss.hitting_member_id and boss.hitting_member_id != member.discord_id:
            await message.channel.send(f'Someone is already hitting B{boss.number} {message.author.mention}', delete_after=5)
            return False
        fiq_iq = boss.get_first_in_queue_id()
        if fiq_iq and member.discord_id != fiq_iq:
            await message.channel.send(f"You don't have priority to hit this boss {message.author.mention}", delete_after=5)
            return False
        member.of_status = 'of' in args or member.of_status
        boss.hitting_member_id = member.discord_id
        member.hitting_boss_number = boss.number
        self.dequeue(member.discord_id, message)
        boss.queue_timeout = None
        member.update()
        boss.update()
        return True

    async def syncing(self, member_id: int, sync_member_id: int, message, *args):
        member = self.find_member(member_id)
        sync_member = self.find_member(sync_member_id)
        boss = self.find_boss(message.id)
        if not member:
            return False
        if not member.hitting_boss_number:
            if not await self.hitting(member_id, message, *args):
                return False
        if not (sync_member and boss):
            return False
        if sync_member.hitting_boss_number:
            await message.channel.send(f'{sync_member.name} is already hitting B{sync_member.hitting_boss_number} {message.author.mention}', delete_after=7)
            return False
        if boss.syncing_member_id:
            old_sync_member = self.find_member(boss.syncing_member_id)
            old_sync_member.hitting_boss_number = 0
            old_sync_member.update()
        boss.syncing_member_id = sync_member.discord_id
        sync_member.hitting_boss_number = boss.number
        self.dequeue(sync_member.discord_id, message)
        boss.queue_timeout = None
        sync_member.update()
        boss.update()
        return True

    def cancel_hit(self, member_id: int, message):
        member = self.find_member(member_id)
        if not member:
            return False
        boss = self.find_boss(member.hitting_boss_number)
        if not boss:
            return False
        if member.hitting_boss_number == boss.number:
            if boss.hitting_member_id == member.discord_id:
                boss.hitting_member_id = 0
                sync_member = self.find_member(boss.syncing_member_id)
                if sync_member:
                    sync_member.hitting_boss_number = 0
                    sync_member.update()
                boss.syncing_member_id = 0
            elif boss.syncing_member_id == member.discord_id:
                boss.syncing_member_id = 0
            member.hitting_boss_number = 0
            if boss.get_first_in_queue_id():
                boss.queue_timeout = cfg.jst_time(minutes=self.timeout_minutes)
            member.update()
            boss.update()
            return boss

    async def done(self, member_id: int, message, *args):
        member = self.find_member(member_id)
        boss = self.find_boss(member.hitting_boss_number)
        if member and boss:
            if args:
                dmg = re.match(r"^([0-9]+\.?[0-9]*([mk])?)", args[0].lower().replace(',', '.'))
                dmg = min(replace_num(dmg.group(0)), boss.hp)
                if dmg:
                    await message.add_reaction(e.ok)
                    member.of_status = 'of' in args or member.of_status
                    if not member.of_status and member.remaining_hits <= 0:
                        await message.channel.send(f"You don't have any hits left {message.author.mention}\nYour hit was counted as Overflow", delete_after=7)
                        member.of_status = True
                    of = member.of_status
                    boss_is_dead = member.deal_damage(dmg, boss)
                    self.add_damage_log(boss, member, dmg, of, boss_is_dead)
                    setattr(self, f'd{self.day}_dmg', getattr(self, f'd{self.day}_dmg') + dmg)
                    self.drive_update()
                    if boss.hitting_member_id == 0:  # if no hitter confirmed within recieve damage
                        boss.queue_timeout = cfg.jst_time(minutes=self.timeout_minutes)
                else:
                    await message.respond(f'Damages not found {message.author.mention}\nUse `{P}done <damage dealt>` to register your hit.\nNumbers ending with K and M are also supported', delete_after=7)
            else:
                await message.respond(f'Argument not found {message.author.mention}\nUse `{P}done <damage dealt>` to register your hit.\nNumbers ending with K and M are also supported', delete_after=7)
        else:
            await message.channel.send(f'You must claim a hit before registering damages {message.author.mention}\nFor example use `{P}h b1` to claim a hit on b1.', delete_after=7)

    # def revive_boss(self, hp):
    #     self.boss_num -= 1
    #     self.current_boss_num = 1 + (self.boss_num - 1) % 5
    #     self.current_boss = self.bosses[self.current_boss_num - 1]
    #     self.current_wave = 1 + (self.boss_num - 1) // 5
    #     self.current_tier = 1 + cfg.tier_threshold.index(max([i for i in cfg.tier_threshold if self.current_wave >= i]))
    #     self.current_boss.hp = min(1000000 * self.current_boss.max_hp[self.current_tier - 1], hp)
    #     self.undo_hit(revive=True)

    # def undo_hit(self, revive=False):
    #     user = self.last_damage_done['member']
    #     day = self.last_damage_done['day']
    #     dmg = self.last_damage_done['amount']
    #     overflow = self.last_damage_done['of']
    #     user.dmg[day - 1] -= dmg
    #     self.dmg[day - 1] -= dmg
    #     if not revive:
    #         self.current_boss.hp += dmg
    #     if not overflow:
    #         user.remaining_hits += 1
    #         user.total_hits -= 1
    #     else:
    #         user.of_status = True
    #     user.update()
    #     self.update()

    async def queue(self, member_id: int, message, *args):
        member = self.find_member(member_id)
        boss = self.find_boss(message.id)
        if not (member and boss):
            return
        if member.hitting_boss_number == boss.number:
            return await message.channel.send(f"You can't queue a boss you are hitting {message.author.mention}", delete_after=7)
        c = self.conn.cursor()
        already_in_queue = c.execute(f'SELECT * from queue WHERE boss_number = {boss.number} AND member_id = {member.discord_id}').fetchone()
        if already_in_queue:
            return await message.channel.send(f"You are already in the queue {message.author.mention}", delete_after=7)
        if 'of' in args:
            member.of_status = True
            member.update()
        if not boss.get_first_in_queue_id():
            boss.queue_timeout = cfg.jst_time(minutes=self.timeout_minutes)
        data = (boss.number, member.discord_id, member.name, False)
        c.execute(f'INSERT INTO queue VALUES {data}')
        self.conn.commit()

    def check_queue(self, message):
        boss = self.find_boss(message.id)
        if not boss:
            return
        if boss.queue_timeout and ((boss.queue_timeout - cfg.jst_time()).total_seconds() <= 0):
            first_in_queue_id = boss.get_first_in_queue_id()
            self.dequeue(first_in_queue_id, message)

    def dequeue(self, member_id: int, message):
        member = self.find_member(member_id)
        boss = self.find_boss(message.id)
        if not (member and boss):
            return
        c = self.conn.cursor()
        c.execute(f'DELETE FROM queue WHERE boss_number = {boss.number} AND member_id = {member.discord_id}')
        self.conn.commit()
        fiq_id = boss.get_first_in_queue_id()
        if fiq_id and fiq_id == member_id:
            boss.queue_timeout = cfg.jst_time(minutes=self.timeout_minutes)

    def add_member(self, member):
        c = self.conn.cursor()
        data = (member.id, member.display_name, 3, 0, 0, 0, 0, 0, 0, 0, False, 0, 0)
        c.execute(f'INSERT INTO members_data VALUES {data}')
        self.members.append(Member(member.id, self.conn))
        self.conn.commit()

    def find_member(self, member_id: int):
        for member in self.members:
            if member.discord_id == member_id:
                return member

    def find_boss(self, message_id_or_boss_number: int):
        for boss in self.bosses:
            if boss.message_id == message_id_or_boss_number or boss.number == message_id_or_boss_number:
                return boss

    def add_damage_log(self, boss, member, damage: int, overflow=False, dead=False):
        c = self.conn.cursor()
        data = (boss.number, boss.wave - 1 * dead, member.discord_id, member.name, damage, overflow, dead)
        c.execute(f'INSERT INTO damage_log VALUES {data}')

    def daily_reset(self):
        # self.rush_hour = False
        self.day = math.ceil((cfg.jst_time() - cfg.cb_start_date).total_seconds() / 60 / 60 / 24)
        print('\nDay {} hits :'.format(self.day - 1))
        for member in self.members:
            if member.remaining_hits > 0:
                print('{0.name} had {0.remaining_hits} hits left'.format(member))
                member.missed_hits += member.remaining_hits
            member.remaining_hits = 3
            member.of_status = False
            member.of_number = 0
            member.update()
        self.drive_update()

    def log(self, message):
        if message.content:
            jst = message.created_at.astimezone(pytz.timezone('Japan')).strftime("%m/%d/%Y %H:%M:%S")
            log = (jst, message.author.display_name, message.clean_content)
            c = self.conn.cursor()
            c.execute(f'INSERT INTO chat_log VALUES {log}')
            self.conn.commit()


class Member:
    def __init__(self, discord_id: int, conn):
        self.conn = conn
        c = self.conn.cursor()
        data = c.execute(f'select * from members_data where discord_id = {discord_id}').fetchone()
        if data:
            columns = c.execute("PRAGMA table_info(members_data)").fetchall()
            for column in columns:
                if data[column[0]] is not None:
                    setattr(self, column[1], data[column[0]])
            self.role_cd = cfg.jst_time()

    def update(self):
        c = self.conn.cursor()
        for key, val in self.__dict__.items():
            try:
                c.execute(f'UPDATE members_data SET {key} = {val} WHERE discord_id = {self.discord_id}')
            except sqlite3.OperationalError:
                pass
        self.conn.commit()

    def deal_damage(self, damage, boss):
        boss_is_dead = boss.recieve_damage(damage, self.discord_id)
        setattr(self, f'b{boss.number}_hits', getattr(self, f'b{boss.number}_hits') + 1)
        if self.of_status:
            self.of_number -= 1
            if self.of_number < 0:
                self.of_number = 0
            self.of_status = False
        else:
            self.remaining_hits -= 1
            if boss_is_dead:
                self.of_number += 1
        self.hitting_boss_number = 0
        self.total_hits += 1
        self.update()
        return boss_is_dead


class Boss():
    def __init__(self, data: dict, clan):
        self.conn = clan.conn
        c = self.conn.cursor()
        for key, val in data.items():
            setattr(self, key, val)
        boss_data = c.execute(f'select * from boss_data where number = {self.number}').fetchone()
        if boss_data:
            boss_columns = c.execute("PRAGMA table_info(boss_data)").fetchall()
            for boss_column in boss_columns:
                if boss_data[boss_column[0]] is not None:
                    setattr(self, boss_column[1], boss_data[boss_column[0]])

        self.tier = 1 + cfg.tier_threshold.index(max([i for i in cfg.tier_threshold if self.wave >= i]))
        self.queue_timeout = cfg.jst_time(minutes=clan.timeout_minutes)

    def update(self):
        c = self.conn.cursor()
        for key, val in self.__dict__.items():
            try:
                c.execute(f'UPDATE boss_data SET {key} = {val} WHERE number = {self.number}')
            except sqlite3.OperationalError:
                pass
        self.conn.commit()

    def recieve_damage(self, damage: int, member_id: int):
        if self.hitting_member_id == member_id:  # reset hitter
            self.hitting_member_id = 0
        elif self.syncing_member_id == member_id:  # reset syncer
            self.syncing_member_id = 0
        if self.hitting_member_id == 0 and self.syncing_member_id > 0:  # reset hitter -> syncer becomes hitter
            self.hitting_member_id = self.syncing_member_id
            self.syncing_member_id = 0
        self.hp -= damage
        if self.hp <= 0:
            self.next()
            return True
        self.update()
        return False

    def next(self):
        self.wave += 1
        self.tier = 1 + cfg.tier_threshold.index(max([i for i in cfg.tier_threshold if self.wave >= i]))
        self.hp = self.max_hp[self.tier - 1] * 10 ** 6
        self.update()

    def get_damage_log(self, wave_offset=0):
        c = self.conn.cursor()
        data = c.execute(f'SELECT * from damage_log WHERE boss_number = {self.number} AND boss_wave = {self.wave + wave_offset}').fetchall()
        if not data:
            return None
        hits = []
        columns = c.execute("PRAGMA table_info(damage_log)").fetchall()
        for hit in data:
            hit_dict = {}
            for column in columns:
                if hit[column[0]] is not None:
                    hit_dict[column[1]] = hit[column[0]]
            hits.append(hit_dict)
        return hits

    def get_queue(self):
        c = self.conn.cursor()
        data = c.execute(f'SELECT * from queue WHERE boss_number = {self.number}').fetchall()
        if not data:
            return None
        queue = []
        columns = c.execute("PRAGMA table_info(queue)").fetchall()
        for member in data:
            member_dict = {}
            for column in columns:
                if member[column[0]] is not None:
                    member_dict[column[1]] = member[column[0]]
            queue.append(member_dict)
        return queue

    def get_first_in_queue_id(self):
        queue = self.get_queue()
        if not queue:
            return None
        return int(queue[0]['member_id'])


def replace_num(num):
    if num[-1] in ['k', 'm']:
        return int(float(num[:-1]) * 10 ** (3 + 3 * (num[-1] == 'm')))
    return int(float(num))


def create_cb_db(name, guild_id, channel_id):
    conn = sqlite3.connect(f'{name}.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE cb_data
                (name text,
                guild_id int,
                channel_id int,
                overview_message_id int,
                d1_dmg int,
                d2_dmg int ,
                d3_dmg int,
                d4_dmg int,
                d5_dmg int,
                rush_hour boolean)''')
    c.execute(f'INSERT INTO cb_data VALUES ("{name}", {guild_id}, {channel_id}, 0, 0, 0, 0, 0, 0, False)')

    c.execute('''CREATE TABLE members_data
                (discord_id int,
                name text,
                remaining_hits int,
                total_hits int,
                b1_hits int,
                b2_hits int,
                b3_hits int,
                b4_hits int,
                b5_hits int,
                hitting_boss_number int,
                of_status boolean,
                of_number int,
                missed_hits int)''')

    c.execute('''CREATE TABLE boss_data
                (number int,
                wave int,
                hp int,
                message_id int,
                hitting_member_id int,
                syncing_member_id int)''')
    for boss in cfg.boss_data:
        data = (boss['number'], boss['wave'], boss['hp'], 0, 0, 0)
        c.execute(f'INSERT INTO boss_data VALUES {data}')

    c.execute('''CREATE TABLE chat_log
                (date_jst text,
                name text,
                message text)''')

    c.execute('''CREATE TABLE damage_log
                (boss_number int,
                boss_wave int,
                member_id int,
                member_name text,
                damage int,
                overflow bool,
                dead bool)''')

    c.execute('''CREATE TABLE queue
                (boss_number int,
                member_id int,
                member_name text,
                pinged bool)''')
    conn.commit()
    conn.close()


def get_csv_table_data(table, c, r=False):
    row_name = [itemgetter(1)(col) for col in c.execute(f"PRAGMA table_info({table})").fetchall()]
    data = None
    if r:
        data = [row_name] + list(reversed(c.execute(f'select * from {table}').fetchall()))
    else:
        data = [row_name] + c.execute(f'select * from {table}').fetchall()
    return data


def data_csv(name):
    conn = sqlite3.connect(f'{name}.db')
    c = conn.cursor()
    table_list = ['members_data']
    path = f'{name}_data.csv'
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for table in table_list:
            writer.writerows(get_csv_table_data(table, c))
            writer.writerow('')
        writer.writerow(['Last updated at', cfg.jst_time().strftime("%m/%d/%Y %H:%M:%S"), 'JST'])
    return path


def chat_log_csv(name):
    conn = sqlite3.connect(f'{name}.db')
    c = conn.cursor()
    path = name + '_chat_log.csv'
    chat_logs = get_csv_table_data('chat_log', c, r=True)
    damage_logs = get_csv_table_data('damage_log', c, r=True)
    data = []
    for a, b in list(zip_longest(chat_logs, damage_logs, fillvalue='')):
        data.append([*a, '', *b])
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(data)
    return path


def togspread(path, ws, gs_sheet):
    content = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            content.append(row)
    ws.clear()
    gs_sheet.values_update(
        ws.title,
        params={'valueInputOption': 'USER_ENTERED'},
        body={'values': content}
    )


def upload_db(path):
    folderName = 'cb-database'
    folders = drive.ListFile(
        {'q': f"title='{folderName}' and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
    for folder in folders:
        if folder['title'] == folderName:
            file_list = drive.ListFile({'q': "'{}' in parents and trashed=false".format(folder['id'])}).GetList()
            file = None
            for drive_file in file_list:
                if drive_file['title'] == path:
                    file = drive_file
                    break
            if not file:
                file = drive.CreateFile({'parents': [{'id': folder['id']}]})
            file.SetContentFile(path)
            file.Upload()
            return True
    return False


def download_db(name):
    folderName = 'cb-database'
    folders = drive.ListFile(
        {'q': "title='" + folderName + "' and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
    for folder in folders:
        if folder['title'] == folderName:
            file_list = drive.ListFile({'q': "'{}' in parents and trashed=false".format(folder['id'])}).GetList()
            for file in file_list:
                if file['title'] == name:
                    file.GetContentFile(name)
                    return True
    return False


def update_db(clan):
    data_path = data_csv(clan.name)
    chat_log_path = chat_log_csv(clan.name)
    togspread(data_path, clan.gs_db, clan.gs_sheet)
    togspread(chat_log_path, clan.gs_chat_log, clan.gs_sheet)
    upload_db(f"{clan.name}.db")
    os.remove(data_path)
    os.remove(chat_log_path)


if __name__ == "__main__":
    pass
    conn = sqlite3.connect('cb_debug.db')
    c = conn.cursor()
    a = c.execute('').fetchall()
    print(a)
    chat_log_csv('cb_debug')
