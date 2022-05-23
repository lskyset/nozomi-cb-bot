import sys
from dataclasses import dataclass
from unittest.mock import MagicMock

sys.modules["datetime"] = MagicMock()
import datetime  # noqa: E402


@dataclass(frozen=True)
class BotConfig:
    PREFIX: str = "!"
    DEFAULT_BOT_ENV: int = 0
    BOT_ENV: int = 0
    DISCORD_TOKEN: str | None = "DISCORD_TOKEN"


@dataclass(frozen=True)
class GoogleSpreadsheetConfig:
    SHEET_KEY: str
    CHAT_LOG_WORKSHEET_NAME: str
    DATA_WORKSHEET_NAME: str


@dataclass
class ClanConfig:
    name: str
    GUILD_ID: int
    CHANNEL_ID: int
    CLAN_ROLE_ID: int
    CLAN_MOD_ROLE_ID: int
    CLAN_ENV: int = BotConfig.DEFAULT_BOT_ENV
    timeout_minutes: int = 15
    skip_line: int = 0
    GOOGLE_SHEET_CONFIG: GoogleSpreadsheetConfig | dict | None = None

    def __post_init__(self) -> None:
        if type(self.GOOGLE_SHEET_CONFIG) is dict:
            self.GOOGLE_SHEET_CONFIG = GoogleSpreadsheetConfig(
                **self.GOOGLE_SHEET_CONFIG
            )


def mock_ClanConfig(
    name: str = "test",
    guild_id: int = 0,
    channel_id: int = 0,
    clan_role_id: int = 0,
    clan_mod_role_id: int = 0,
) -> ClanConfig:
    return ClanConfig(
        name=name,
        GUILD_ID=guild_id,
        CHANNEL_ID=channel_id,
        CLAN_ROLE_ID=clan_role_id,
        CLAN_MOD_ROLE_ID=clan_mod_role_id,
    )


@dataclass(frozen=True)
class BossData:
    NAME: str
    NUMBER: int
    IMG_URL: str
    MAX_HP_LIST: list[int]


def mock_BossData(boss_number: int = 1) -> BossData:
    return BossData(
        NAME=f"boss{boss_number}",
        NUMBER=boss_number,
        IMG_URL=f"{boss_number}.png",
        MAX_HP_LIST=[boss_number] * 5,
    )


@dataclass(frozen=True)
class PricoCbData:
    CB_ID: int
    TIER_THRESHOLD: list[int]
    START_DATE: datetime.datetime
    END_DATE: datetime.datetime
    BOSSES_DATA: list[BossData]


def mock_PricoCbData(
    cb_id: int = 0,
    tier_threshold: list | None = None,
    start_date: datetime.datetime | None = None,
    end_date: datetime.datetime | None = None,
    bosses_data: list[BossData] | None = None,
) -> PricoCbData:
    return PricoCbData(
        CB_ID=cb_id,
        TIER_THRESHOLD=tier_threshold or [1, 2, 3, 4, 5],
        START_DATE=start_date or datetime.datetime(0, 0, 0),
        END_DATE=end_date or datetime.datetime(0, 0, 0),
        BOSSES_DATA=bosses_data or [mock_BossData(i) for i in range(5)],
    )


def jst_time():
    return datetime.datetime.now()


CB_DATA = mock_PricoCbData()
# GC, DRIVE = (None, None)
