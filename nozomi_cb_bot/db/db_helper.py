import sqlite3

from nozomi_cb_bot.config import CB_DATA


def create_cb_db(name, guild_id, channel_id):
    conn = sqlite3.connect(f"{name}.db")
    c = conn.cursor()
    c.execute(
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
    c.execute(
        "INSERT INTO cb_data VALUES (?, ?, ?, 0, 0, 0, 0, 0, 0, False)",
        (name, guild_id, channel_id),
    )

    c.execute(
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

    c.execute(
        """CREATE TABLE boss_data
                (number int,
                wave int,
                hp int,
                message_id int,
                hitting_member_id int,
                syncing_member_id int)"""
    )
    for boss in CB_DATA.BOSSES_DATA:
        data = (boss.NUMBER, boss.MAX_HP_LIST[0])
        c.execute("INSERT INTO boss_data VALUES (?,1,?,0,0,0)", data)

    c.execute(
        """CREATE TABLE chat_log
                (date_jst text,
                name text,
                message text)"""
    )

    c.execute(
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

    c.execute(
        """CREATE TABLE queue
                (boss_number int,
                member_id int,
                member_name text,
                pinged bool,
                note text,
                timestamp int,
                wave int)"""
    )

    c.execute(
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
    conn.commit()
    conn.close()
