import json
import os

from nozomi_cb_bot.cb.clan import Clan
from nozomi_cb_bot.config import CB_DATA, ClanConfig
from nozomi_cb_bot.db import GoogleDriveDatabase, SqliteDatabase

# from nozomi_cb_bot.db.google_drive_db import GoogleDriveDatabase


class ClanManager:
    def __init__(self, allowed_env: int) -> None:
        self._clans: list[Clan] = []
        self.allowed_env = allowed_env

    @property
    def clans(self) -> list[Clan]:
        """This manager's `clans` list"""
        return self._clans

    def find_clan_by_id(self, guild_id: int, channel_id: int) -> Clan | None:
        """Returns the first Clan from this manager's `clans` list that has mathcing `GUILD_ID` and `CHANNEL_ID` with the arguments.

        If no Clan is found returns None instead."""

        for clan in self._clans:
            if (
                clan.config.GUILD_ID == guild_id
                and clan.config.CHANNEL_ID == channel_id
            ):
                return clan
        return None

    def create_clan(self, clan_config: ClanConfig) -> Clan | None:
        """Creates a new `Clan` instance and adds it to this manager's `clans` list."""

        if clan_config.CLAN_ENV != self.allowed_env:
            return print(
                f"{clan_config.name} Clan wasn't created because it's `{clan_config.CLAN_ENV=}` doesn't match with this manager's `{self.allowed_env=}`"
            )
        if clan_config.CLAN_ENV > 0:
            clan_config.name += "_dev"
        clan_db: SqliteDatabase | GoogleDriveDatabase
        if clan_config.GOOGLE_SHEET_CONFIG is None:
            clan_db = SqliteDatabase(clan_config, CB_DATA)
        else:
            clan_db = GoogleDriveDatabase(clan_config, CB_DATA)
        clan = Clan(clan_config, clan_db, CB_DATA)
        self._clans.append(clan)
        return clan

    def load_clans_from_config(
        self, clans_config_file_path="./volume/clans_config.json"
    ) -> None:
        """Creates new `Clan` instances from all the clans specified in the clan config file where `CLAN_ENV` matches the manager's `allowed_env` number and add them to the manager's `clans` list.

        Creates a default clans config file if the file doesn't exists."""

        if os.path.isfile(clans_config_file_path):
            with open(clans_config_file_path, "r") as clans_cfg:
                [
                    self.create_clan(ClanConfig(clan_name, **clan_config))
                    for clan_name, clan_config in json.load(clans_cfg).items()
                ]
        # else:
        #     print(f"{clans_config_file_path} not found.")
        #     with open(clans_config_file_path, "w") as fd:
        #         fd.write(json.dumps(ClanConfig(), indent=4))
        #         print(f"Created a default {clans_config_file_path}.")
