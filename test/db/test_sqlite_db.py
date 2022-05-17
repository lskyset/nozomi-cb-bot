import sys
from test.helpers import mock_config
from test.helpers.mock_config import mock_ClanConfig, mock_PricoCbData

import pytest


@pytest.fixture
def sqlite_db(mocker, mock_sqlite3):
    sys.modules["os"] = mocker.MagicMock()
    sys.modules["sqlite3"] = mock_sqlite3
    sys.modules["nozomi_cb_bot.cb"] = mocker.MagicMock()
    sys.modules["nozomi_cb_bot.config"] = mock_config
    from nozomi_cb_bot.db import sqlite_db

    return sqlite_db


@pytest.fixture
def mock_sqlite3(mocker):
    import sqlite3

    mocker.patch("sqlite3.Connection")
    mocker.patch("sqlite3.connect", return_value=sqlite3.Connection)
    mocker.patch("sqlite3.Cursor")
    mocker.patch("sqlite3.Connection.cursor", return_value=sqlite3.Cursor)
    return sqlite3


def default_SqliteDatabase(sqlite_db):
    return sqlite_db.SqliteDatabase(mock_ClanConfig(), mock_PricoCbData())


class Test_SqliteDatabase:
    def test_init(self, sqlite_db, mocker):
        clan_config = mock_ClanConfig()
        cb_data = mock_PricoCbData()
        init = mocker.spy(sqlite_db.SqliteDatabase, "__init__")
        dsdb = sqlite_db.SqliteDatabase(clan_config, cb_data)
        assert dsdb._clan_config == clan_config
        assert dsdb._cb_data == cb_data
        assert dsdb._db_path == f"{clan_config.name}.db"
        init.assert_called_once_with(dsdb, clan_config, cb_data)

    def test_connect(self, sqlite_db, mocker):
        connect = mocker.spy(sqlite_db.SqliteDatabase, "connect")
        dsdb = default_SqliteDatabase(sqlite_db)
        connect.assert_called_once_with(dsdb)

    def test_initialize_cb(self, sqlite_db, mocker):
        initialize_cb = mocker.spy(sqlite_db.SqliteDatabase, "initialize_cb")
        default_SqliteDatabase(sqlite_db)
        initialize_cb.assert_not_called()

    def test_save(self, sqlite_db, mocker):
        _save = mocker.spy(sqlite_db.SqliteDatabase, "_save")
        default_SqliteDatabase(sqlite_db)
        _save.assert_not_called()

    def test_create_tables(self, sqlite_db, mocker):
        _create_tables = mocker.spy(sqlite_db.SqliteDatabase, "_create_tables")
        default_SqliteDatabase(sqlite_db)
        _create_tables.assert_not_called()
