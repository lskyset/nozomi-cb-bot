import sqlite3
from dataclasses import dataclass
from datetime import datetime

from nozomi_cb_bot import config as cfg
from nozomi_cb_bot.config import CB_DATA


@dataclass
class Boss:
    def __init__(self, data: cfg.BossData, clan):
        self.wave = -1
        self.message_id = -1
        self.number = data.NUMBER
        self.hitting_member_id = -1
        self.syncing_member_id = -1
        self.name = data.NAME
        self.max_hp: list[int] = data.MAX_HP_LIST
        self.img = data.IMG_URL
        self.conn = clan.conn
        c = self.conn.cursor()
        boss_data = c.execute(
            f"SELECT * from boss_data where number = {self.number}"
        ).fetchone()
        if boss_data:
            boss_columns = c.execute("PRAGMA table_info(boss_data)").fetchall()
            for boss_column in boss_columns:
                if boss_data[boss_column[0]] is not None:
                    setattr(self, boss_column[1], boss_data[boss_column[0]])

        self.tier = 1 + CB_DATA.TIER_THRESHOLD.index(
            max([i for i in CB_DATA.TIER_THRESHOLD if self.wave >= i])
        )
        self.queue_timeout: datetime | None = cfg.jst_time(minutes=clan.timeout_minutes)

    def update(self):
        c = self.conn.cursor()
        for key, val in self.__dict__.items():
            try:
                c.execute(
                    f"UPDATE boss_data SET {key} = ? WHERE number = ?",
                    (val, self.number),
                )
            except sqlite3.OperationalError:
                pass
        self.conn.commit()

    def recieve_damage(self, damage: int, member_id: int):
        if self.hitting_member_id == member_id:  # reset hitter
            self.hitting_member_id = 0
        elif self.syncing_member_id == member_id:  # reset syncer
            self.syncing_member_id = 0
        if (
            self.hitting_member_id == 0 and self.syncing_member_id > 0
        ):  # reset hitter -> syncer becomes hitter
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
        self.tier = 1 + CB_DATA.TIER_THRESHOLD.index(
            max([i for i in CB_DATA.TIER_THRESHOLD if self.wave >= i])
        )
        self.hp = self.max_hp[self.tier - 1]
        self.update()

    def get_damage_log(self, wave_offset=0):
        c = self.conn.cursor()
        data = c.execute(
            f"SELECT * from damage_log WHERE boss_number = {self.number} AND boss_wave = {self.wave + wave_offset} ORDER BY timestamp"
        ).fetchall()
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
        data = c.execute(
            f"SELECT * from queue WHERE boss_number = {self.number} and wave = {self.wave}"
        ).fetchall()
        data += c.execute(
            f"SELECT * from queue WHERE boss_number = {self.number} and wave < {self.wave}"
        ).fetchall()
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

    def get_waiting(self):
        c = self.conn.cursor()
        data = c.execute(
            f"SELECT * from queue WHERE boss_number = {self.number} and wave > {self.wave} ORDER BY wave"
        ).fetchall()
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
        return int(queue[0]["member_id"])
