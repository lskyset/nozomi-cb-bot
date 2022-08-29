import os
import sqlite3

import discord

from nozomi_cb_bot import cb
from nozomi_cb_bot.config import ClanConfig, PricoCbData


class SqliteDatabase:
    def __init__(self, clan_config: ClanConfig, cb_data: PricoCbData) -> None:
        self._clan_config = clan_config
        self._cb_data = cb_data

        self._db_path = f"./volume/{clan_config.name}.db"
        if not os.path.exists(self._db_path):
            self._connect()
            self._create_tables()
            self._initialize_cb()
            print(f"Created {self._db_path}")
        else:
            self._connect()

    def _connect(self, path: str | None = None) -> None:
        if path:
            self._db_path = path
        self._conn = sqlite3.connect(self._db_path)
        self._c = self._conn.cursor()

    def _initialize_cb(self) -> None:
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

    def save_clan(self, clan: cb.Clan) -> None:
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
        self._save()

    def _get_boss_data(self, message_id):
        data = self._c.execute(
            "SELECT * from boss_data where message_id = ?", (message_id,)
        ).fetchone()
        if not data:
            return None
        return data

    def get_boss(self, clan: cb.Clan, message: discord.Message) -> cb.Boss | None:
        boss_data = self._get_boss_data(message.id)
        if boss_data is None:
            return None
        return cb.Boss(  # type: ignore
            *boss_data,
            self._cb_data,
            self,
            clan,
            message,
        )

    def get_all_bosses(self, clan: cb.Clan) -> list[cb.Boss] | None:
        bosses_data = self._c.execute("SELECT * from boss_data").fetchall()
        if not bosses_data:
            return None
        return [
            cb.Boss(  # type: ignore
                *boss_data,
                self._cb_data,
                self,
                clan,
            )
            for boss_data in bosses_data
        ]

    def _save_boss(self, boss: cb.Boss, save: bool) -> None:
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
        if save:
            self._save()

    def save_boss(self, boss: cb.Boss) -> None:
        return self._save_boss(boss, save=True)

    def save_bosses(self, bosses: list[cb.Boss]) -> None:
        for boss in bosses:
            self._save_boss(boss, save=False)
        self._save()

    def _add_member(
        self, clan: cb.Clan, member: discord.Member, save: bool
    ) -> cb.Member:
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
        if save:
            self._save()
        return cb_member

    def add_member(self, clan: cb.Clan, member: discord.Member) -> cb.Member:
        return self._add_member(clan, member, save=True)

    def add_members(
        self, clan: cb.Clan, members: list[discord.Member]
    ) -> list[cb.Member]:
        ret = [self._add_member(clan, member, save=False) for member in members]
        self._save()
        return ret

    def _get_member_data(self, member_id: int) -> list | None:
        data = self._c.execute(
            f"SELECT * from members_data WHERE discord_id = {member_id}"
        ).fetchone()
        if not data:
            return None
        return data

    def get_member(self, clan: cb.Clan, member: discord.Member) -> cb.Member | None:
        member_data = self._get_member_data(member.id)
        if member_data is None:
            return None
        return cb.Member(  # type: ignore
            *member_data,
            self._cb_data,
            self,
            clan,
            member,
        )

    def get_members(
        self, clan: cb.Clan, members: list[discord.Member]
    ) -> list[cb.Member]:
        ret = []
        for member in members:
            if clan_member := self.get_member(clan, member):
                ret.append(clan_member)
        return ret

    def save_member(self, member: cb.Member) -> None:
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

    def save_members(self, members: list[cb.Member]) -> None:
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
