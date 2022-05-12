import sqlite3

from nozomi_cb_bot.db import db_helper


def test_sqlite_connect(mocker):
    mocker.patch("sqlite3.connect")
    db_helper.create_cb_db("test", 0, 0)
    sqlite3.connect.assert_called_once_with("test.db")
