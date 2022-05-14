import sqlite3

from nozomi_cb_bot import config as cfg


class Member:
    def __init__(self, discord_id: int, conn):
        self.discord_id = -1
        self.conn = conn
        self.remaining_hits = -1
        c = self.conn.cursor()
        data = c.execute(
            f"SELECT * from members_data where discord_id = {discord_id}"
        ).fetchone()
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
                c.execute(
                    f"UPDATE members_data SET {key} = ? WHERE discord_id = ?",
                    (val, self.discord_id),
                )
            except sqlite3.OperationalError:
                pass
        self.conn.commit()

    def deal_damage(self, damage, boss):
        boss_is_dead = boss.recieve_damage(damage, self.discord_id)
        setattr(self, f"b{boss.number}_hits", getattr(self, f"b{boss.number}_hits") + 1)
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
