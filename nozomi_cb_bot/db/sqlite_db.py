import os
import sqlite3

import discord

from nozomi_cb_bot import cb
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
            "INSERT INTO cb_data VALUES (?, ?, ?, null, 0, 0, 0, 0, 0)",
            (
                self._clan_config.name,
                self._clan_config.GUILD_ID,
                self._clan_config.CHANNEL_ID,
            ),
        )
        for boss in self._cb_data.BOSSES_DATA:
            self._c.execute(
                "INSERT INTO boss_data VALUES (?,?,?,null,null,null)",
                (boss.NUMBER, 1, boss.MAX_HP_LIST[0]),
            )
        self._save()

    def save_clan(self, clan: cb.Clan):
        self._c.execute(
            """UPDATE cb_data SET
                    name = ?,
                    guild_id = ?,
                    channel_id = ?,
                    overview_message_id = ?,
                    d1_dmg = ?,
                    d2_dmg = ?,
                    d3_dmg = ?,
                    d4_dmg = ?,
                    d5_dmg = ?""",
            (
                clan.config.name,
                clan.config.GUILD_ID,
                clan.config.CHANNEL_ID,
                clan.overview_message_id,
                clan.d1_dmg,
                clan.d2_dmg,
                clan.d3_dmg,
                clan.d4_dmg,
                clan.d5_dmg,
            ),
        )

    def get_boss_from_message_id(self, clan: cb.Clan, message_id: int) -> cb.Boss:
        return cb.Boss(  # type: ignore
            *self._c.execute(
                "SELECT * from boss_data where message_id = ?", (message_id,)
            ).fetchone(),
            self._cb_data,
            self,
            clan,
        )

    def get_bosses(self, clan: cb.Clan) -> list[cb.Boss]:
        return [
            cb.Boss(  # type: ignore
                *db_boss_data,
                self._cb_data,
                self,
                clan,
            )
            for db_boss_data in self._c.execute("SELECT * from boss_data").fetchall()
        ]

    def add_member(self, clan: cb.Clan, member: discord.Member) -> cb.Member:
        member_data = (
            member.id,
            member.display_name,
            3,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            False,
            0,
            0,
        )
        cb_member = cb.Member(
            *member_data,
            self._cb_data,
            self,
            clan,
            member,
        )
        self._c.execute(
            "INSERT INTO members_data VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            member_data,
        )
        self._c.execute(
            "INSERT INTO missed_hits_data VALUES (?,?,0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)",
            (member.id, member.display_name),
        )
        return cb_member

    def get_members(
        self, clan: cb.Clan, members: list[discord.Member]
    ) -> list[cb.Member]:
        member_list = []
        for member in members:
            member_data: tuple = self._c.execute(
                f"SELECT * from members_data WHERE discord_id = {member.id}"
            ).fetchone()
            if not member_data:
                member_list.append(self.add_member(clan, member))
            else:
                member_list.append(
                    cb.Member(  # type: ignore
                        *member_data,
                        self._cb_data,
                        self,
                        clan,
                        member,
                    )
                )
        return member_list

    def save_boss(self, boss: cb.Boss) -> None:
        self._c.execute(
            """UPDATE boss_data SET
                    wave = ?,
                    hp = ?,
                    message_id = ?,
                    hitting_member_id = ?,
                    syncing_member_id = ?
                WHERE number = ?""",
            (
                boss.wave,
                boss.hp,
                boss.message_id,
                boss.hitting_member_id,
                boss.syncing_member_id,
                boss.number,
            ),
        )

        self._save()

    def save_bosses(self, bosses: list[cb.Boss]) -> None:
        for boss in bosses:
            self.save_boss(boss)

    def save_member(self, member: cb.Member):
        self._c.execute(
            """UPDATE members_data SET
                    name = ?,
                    remaining_hits = ?,
                    total_hits = ?,
                    b1_hits = ?,
                    b2_hits = ?,
                    b3_hits = ?,
                    b4_hits = ?,
                    b5_hits = ?,
                    hitting_boss_number = ?,
                    of_status = ?,
                    of_number = ?,
                    missed_hits = ?
                WHERE discord_id = ?""",
            (
                member.name,
                member.remaining_hits,
                member.total_hits,
                member.b1_hits,
                member.b2_hits,
                member.b3_hits,
                member.b4_hits,
                member.b5_hits,
                member.hitting_boss_number,
                member.of_status,
                member.of_number,
                member.missed_hits,
                member.discord_id,
            ),
        )
        self._save()

    def save_members(self, members: list[cb.Member]):
        for member in members:
            self.save_member(member)

    def _save(self) -> None:
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
                    d5_dmg int)"""
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
        self._save()
