from __future__ import annotations

import sqlite3
from itertools import zip_longest
from operator import itemgetter
from typing import TYPE_CHECKING

from nozomi_cb_bot.config import GC, GoogleSpreadsheetConfig, jst_time

if TYPE_CHECKING:
    import gspread


class GspreadUi:
    def __init__(
        self,
        gspread_config: GoogleSpreadsheetConfig,
        db_c: sqlite3.Cursor,
    ) -> None:
        self._config = gspread_config
        self._c = db_c
        if GC is not None:
            self._gs_sheet = GC.open_by_key(self._config.SHEET_KEY)
        self._gs_data = self._gs_sheet.worksheet(self._config.DATA_WORKSHEET_NAME)
        self._gs_chat_log = self._gs_sheet.worksheet(
            self._config.CHAT_LOG_WORKSHEET_NAME
        )

    def _togspread(self, content: list[list], ws: gspread.Worksheet):
        ws.clear()
        self._gs_sheet.values_update(
            ws.title,
            params={"valueInputOption": "USER_ENTERED"},
            body={"values": content},
        )

    def _get_table_data(self, table: str, reverse=False) -> list:
        row_name = [
            itemgetter(1)(col)
            for col in self._c.execute(f"PRAGMA table_info({table})").fetchall()
        ]
        data = None
        if reverse:
            data = [row_name] + list(
                reversed(self._c.execute(f"SELECT * from {table}").fetchall())
            )
        else:
            data = [row_name] + self._c.execute(f"SELECT * from {table}").fetchall()
        return data

    def get_clan_data(self) -> list[list[str]]:
        table_list = ["members_data"]
        data = []
        for table in table_list:
            for row in self._get_table_data(table):
                data.append(list(map(str, row)))
            data.append([""])
        data.append(
            ["Last updated at", jst_time().strftime("%m/%d/%Y %H:%M:%S"), "JST"]
        )
        return data

    def get_logs_data(self) -> list[list[str]]:
        chat_logs = self._get_table_data("chat_log")
        damage_logs = self._get_table_data("damage_log")
        data = []
        for a, b in list(zip_longest(chat_logs, damage_logs, fillvalue="")):
            data.append([*map(str, a), "", *map(str, b)])
        return data

    def _update(self):
        self._togspread(self.get_clan_data(), self._gs_data)
        self._togspread(self.get_logs_data(), self._gs_chat_log)
