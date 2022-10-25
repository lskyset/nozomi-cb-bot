import os
import time

import discord

from nozomi_cb_bot import cb
from nozomi_cb_bot.config import DRIVE, ClanConfig, PricoCbData
from nozomi_cb_bot.db.sqlite_db import SqliteDatabase
from nozomi_cb_bot.google_spreadsheet_ui.gspread_ui import GspreadUi


class GoogleDriveDatabase:
    def __init__(self, clan_config: ClanConfig, cb_data: PricoCbData) -> None:
        self._clan_config = clan_config
        self._cb_data = cb_data

        self._loading = False

        self._db_path = f"volume/{clan_config.name}.db"

        if DRIVE is None:
            raise Exception("no drive found")
        self._drive = DRIVE
        if not os.path.exists(self._db_path):
            self._download()
        self._sqlite_db = SqliteDatabase(self._clan_config, self._cb_data)
        self._conn = self._sqlite_db._conn  # temp
        self._c = self._sqlite_db._c  # temp
        self._ui = GspreadUi(self._clan_config.GOOGLE_SHEET_CONFIG, self._c)
        self._save()

    def save_clan(self, clan: cb.Clan) -> None:
        self._sqlite_db.save_clan(clan)
        self._save()

    def get_boss(self, clan: cb.Clan, message: discord.Message) -> cb.Boss | None:
        return self._sqlite_db.get_boss(clan, message)

    def get_all_bosses(self, clan: cb.Clan) -> list[cb.Boss] | None:
        return self._sqlite_db.get_all_bosses(clan)

    def save_boss(self, boss: cb.Boss) -> None:
        return self._sqlite_db.save_boss(boss)

    def save_bosses(self, bosses: list[cb.Boss]) -> None:
        return self._sqlite_db.save_bosses(bosses)

    def add_member(self, clan: cb.Clan, member: discord.Member) -> cb.Member:
        return self._sqlite_db.add_member(clan, member)

    def add_members(
        self, clan: cb.Clan, members: list[discord.Member]
    ) -> list[cb.Member]:
        return self._sqlite_db.add_members(clan, members)

    def get_member(self, clan: cb.Clan, member: discord.Member) -> cb.Member | None:
        return self._sqlite_db.get_member(clan, member)

    def get_members(
        self, clan: cb.Clan, members: list[discord.Member]
    ) -> list[cb.Member]:
        return self._sqlite_db.get_members(clan, members)

    def save_member(self, member: cb.Member) -> None:
        return self._sqlite_db.save_member(member)

    def save_members(self, members: list[cb.Member]) -> None:
        return self._sqlite_db.save_members(members)

    def _download(self) -> None:
        folderName = "cb-database"
        folders = self._drive.ListFile(
            {
                "q": "title='"
                + folderName
                + "' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            }
        ).GetList()
        for folder in folders:
            if folder["title"] == folderName:
                file_list = self._drive.ListFile(
                    {"q": "'{}' in parents and trashed=false".format(folder["id"])}
                ).GetList()
                for file in file_list:
                    if file["title"] == self._db_path:
                        file.GetContentFile(self._db_path)

    def _upload(self) -> None:
        folderName = "cb-database"
        folders = self._drive.ListFile(
            {
                "q": f"title='{folderName}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            }
        ).GetList()
        for folder in folders:
            if folder["title"] == folderName:
                file_list = self._drive.ListFile(
                    {"q": "'{}' in parents and trashed=false".format(folder["id"])}
                ).GetList()
                file = None
                for drive_file in file_list:
                    if drive_file["title"] == self._db_path:
                        file = drive_file
                        break
                if not file:
                    file = self._drive.CreateFile({"parents": [{"id": folder["id"]}]})
                file.SetContentFile(self._db_path)
                file.Upload()

    def _save(self) -> None:
        while self._loading:
            time.sleep(1)
        self._loading = True
        self._upload()
        self._ui._update()
        self._loading = False

    def close(self) -> None:
        self._save()
        self._conn.close()
