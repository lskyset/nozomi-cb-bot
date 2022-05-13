from dataclasses import dataclass

import pytest


@pytest.fixture
def db_helper(mocker, mock_sqlite3, mock_config):
    import sys

    sys.modules["sqlite3"] = mock_sqlite3
    sys.modules["nozomi_cb_bot.config"] = mock_config
    from nozomi_cb_bot.db import db_helper

    return db_helper


@pytest.fixture
def mock_sqlite3(mocker):
    import sqlite3

    mocker.patch("sqlite3.Connection")
    mocker.patch("sqlite3.connect", return_value=sqlite3.Connection)
    mocker.patch("sqlite3.Cursor")
    mocker.patch("sqlite3.Connection.cursor", return_value=sqlite3.Cursor)
    return sqlite3


@pytest.fixture
def mock_config(mocker):
    config = mocker.MagicMock()
    config.CB_DATA = MockPricoCbData([MockBossData(i + 1, [1] * 5) for i in range(5)])
    return config


@dataclass
class MockBossData:
    NUMBER: int
    MAX_HP_LIST: list[int]


@dataclass
class MockPricoCbData:
    BOSSES_DATA: list[MockBossData]


class Test_create_cb_db:
    def test_return(self, db_helper):
        assert db_helper.create_cb_db("test", 0, 0) is None

    def test_sqlite_connect(self, db_helper):
        db_helper.create_cb_db("test", 0, 0)
        db_helper.sqlite3.connect.assert_called_once_with("test.db")

    def test_sqlite_execute(self, db_helper):
        db_helper.create_cb_db("test", 0, 0)
        assert db_helper.sqlite3.Cursor.execute.call_count == 8 + 5  # tables + bosses

    def test_sqlite_commit(self, db_helper):
        db_helper.create_cb_db("test", 0, 0)
        db_helper.sqlite3.Connection.commit.assert_called_once_with()

    def test_sqlite_close(self, db_helper):
        db_helper.create_cb_db("test", 0, 0)
        db_helper.sqlite3.Connection.close.assert_called_once_with()


# @pytest.fixture
# def mock_sqlite3(mocker):
#     import sqlite3

#     mocker.patch("sqlite3.Cursor.execute")
#     mocker.patch("sqlite3.Connection")
#     mocker.patch("sqlite3.connect", return_value=sqlite3.Connection)
#     return sqlite3


# def test_sqlite_connect(db_helper, mock_sqlite3):
#     db_helper.create_cb_db("test_connect", 0, 0)
#     mock_sqlite3.connect.assert_called_once_with("test_connect.db")


# def test_sqlite_connect2(db_helper, mock_sqlite3):
#     db_helper.create_cb_db("test_connect", 0, 0)
#     mock_sqlite3.connect.assert_called_once_with("test_connect.db")


# def test_sqlite_cursor(db_helper, mock_sqlite3):
#     db_helper.create_cb_db("test_cursor", 0, 0)
#     mock_sqlite3.Connection.cursor.assert_called_once()


# def test_sqlite_execute(db_helper, mock_sqlite3):
#     db_helper.create_cb_db("test_execute", 0, 0)
#     mock_sqlite3.Connection.cursor.execute.assert_called()


# def test_sqlite_commit(db_helper, mock_sqlite3):
#     db_helper.create_cb_db("test_commit", 0, 0)
#     mock_sqlite3.Connection.commit.assert_called_once()


# def test_sqlite_close(db_helper, mock_sqlite3):
#     db_helper.create_cb_db("test_close", 0, 0)
#     mock_sqlite3.Connection.close.assert_called_once()
