import sqlite3
from unittest import mock


def test_sqlite_connect(mocker):
    mocker.patch("sqlite3.connect")
    import sys

    sys.modules["nozomi_cb_bot.config"] = mock.MagicMock()
    from nozomi_cb_bot.db import db_helper

    db_helper.create_cb_db("test", 0, 0)
    sqlite3.connect.assert_called_once_with("test.db")
