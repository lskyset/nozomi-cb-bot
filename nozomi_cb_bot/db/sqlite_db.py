import os
import sqlite3

from nozomi_cb_bot.cb.boss import Boss
from nozomi_cb_bot.config import ClanConfig, PricoCbData


class SqliteDatabase:
    def __init__(self, clan_config: ClanConfig, cb_data: PricoCbData) -> None:
        self._clan_config = clan_config
        self._cb_data = cb_data

        self._db_path = f"{clan_config.name}.db"
        if not os.path.exists(self._db_path):
            self.connect()
            self._create_tables()
            self.initialize_cb()
            print(f"Created {self._db_path}")
        else:
            self.connect()

    def connect(self, path: str | None = None) -> None:
        if path:
            self._db_path = path
        self._conn = sqlite3.connect(self._db_path)
        self._c = self._conn.cursor()

    def initialize_cb(self) -> None:
        self._c.execute(
            "INSERT INTO cb_data VALUES (?, ?, ?, 0, 0, 0, 0, 0, 0, False)",
            (
                self._clan_config.name,
                self._clan_config.GUILD_ID,
                self._clan_config.CHANNEL_ID,
            ),
        )
        for boss in self._cb_data.BOSSES_DATA:
            self._c.execute(
                "INSERT INTO boss_data VALUES (?,?,?,0,0,0)",
                (boss.NUMBER, 1, boss.MAX_HP_LIST[0]),
            )
        self._update()

    def get_boss_from_message_id(self, message_id: int) -> Boss:
        return Boss(
            *self._c.execute(
                "SELECT * from boss_data where message_id = ?", (message_id,)
            ).fetchone(),
            self._cb_data,
            self,
        )

    def get_bosses(self) -> list[Boss]:
        return [
            Boss(
                *db_boss_data,
                self._cb_data,
                self,
            )
            for db_boss_data in self._c.execute("SELECT * from boss_data").fetchall()
        ]

    def _update(self) -> None:
        self._conn.commit()

    def _create_tables(self) -> None:
        self._c.execute(
            """CREATE TABLE cb_data
                    (name text,
                    guild_id int,
                    channel_id int,
                    overview_message_id int,
                    d1_dmg int,
                    d2_dmg int ,
                    d3_dmg int,
                    d4_dmg int,
                    d5_dmg int,
                    rush_hour boolean)"""
        )

        self._c.execute(
            """CREATE TABLE members_data
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
                    missed_hits int)"""
        )

        self._c.execute(
            """CREATE TABLE boss_data
                    (number int,
                    wave int,
                    hp int,
                    message_id int,
                    hitting_member_id int,
                    syncing_member_id int)"""
        )

        self._c.execute(
            """CREATE TABLE chat_log
                    (date_jst text,
                    name text,
                    message text)"""
        )

        self._c.execute(
            """CREATE TABLE damage_log
                    (boss_number int,
                    boss_wave int,
                    member_id int,
                    member_name text,
                    damage int,
                    overflow bool,
                    dead bool,
                    timestamp int)"""
        )

        self._c.execute(
            """CREATE TABLE queue
                    (boss_number int,
                    member_id int,
                    member_name text,
                    pinged bool,
                    note text,
                    timestamp int,
                    wave int)"""
        )

        self._c.execute(
            """CREATE TABLE missed_hits_data
                    (discord_id int,
                    name text,
                    total_missed_hits int,
                    total_missed_of int,
                    d1_missed_hits int,
                    d2_missed_hits int,
                    d3_missed_hits int,
                    d4_missed_hits int,
                    d5_missed_hits int,
                    d1_missed_of int,
                    d2_missed_of int,
                    d3_missed_of int,
                    d4_missed_of int,
                    d5_missed_of int)"""
        )
        self._update()
