import os
import sqlite3
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta

import gspread
import pytz
from dotenv import find_dotenv, load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

os.makedirs("./volume", exist_ok=True)
print("Loading .env environment variables...")
load_dotenv(find_dotenv("./volume/.env"))


def connect_to_drive() -> tuple[gspread.Client, GoogleDrive] | tuple[None, None]:
    json_creds = os.getenv("JSON_CREDS")
    txt_creds = os.getenv("TXT_CREDS")
    if json_creds is None or txt_creds is None:
        return (None, None)
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    GoogleAuth.DEFAULT_SETTINGS["client_config_file"] = "./volume/client_secrets.json"
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        f"./volume/{json_creds}", scope  # type: ignore
    )
    gc = gspread.authorize(creds)
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile(f"./volume/{txt_creds}")
    drive = GoogleDrive(gauth)
    return (gc, drive)


@dataclass(frozen=True)
class BotConfig:
    PREFIX: str = os.getenv("PREFIX") or "!"
    DEFAULT_BOT_ENV: int = int(os.getenv("DEFAULT_BOT_ENV") or 0)
    BOT_ENV: int = int(os.getenv("BOT_ENV") or 0)
    DISCORD_TOKEN: str | None = os.getenv("DISCORD_TOKEN")


@dataclass(frozen=True)
class GoogleSpreadsheetConfig:
    """Represents a `GoogleDriveDatabase` configuration inside a `ClanConfig` configuration class."""

    SHEET_KEY: str
    CHAT_LOG_WORKSHEET_NAME: str
    DATA_WORKSHEET_NAME: str


@dataclass
class ClanConfig:
    """Represents a `Clan` configuration."""

    name: str
    GUILD_ID: int
    CHANNEL_ID: int
    CLAN_ROLE_ID: int
    CLAN_MOD_ROLE_IDS: list[int]
    CLAN_ENV: int = BotConfig.DEFAULT_BOT_ENV
    timeout_minutes: int = 15
    skip_line: int = 0
    GOOGLE_SHEET_CONFIG: GoogleSpreadsheetConfig | dict | None = None

    def __post_init__(self) -> None:
        if type(self.GOOGLE_SHEET_CONFIG) is dict:
            self.GOOGLE_SHEET_CONFIG = GoogleSpreadsheetConfig(
                **self.GOOGLE_SHEET_CONFIG
            )


@dataclass(frozen=True)
class BossData:
    """Represents a basic boss data extracted from priconne's master.db file."""

    NAME: str
    NUMBER: int
    IMG_URL: str
    MAX_HP_LIST: list[int]


@dataclass(frozen=True)
class PricoCbData:
    """Represents a basic clan battle data extracted from priconne's master.db file."""

    CB_ID: int
    TIER_THRESHOLD: list[int]
    START_DATE: datetime
    END_DATE: datetime
    BOSSES_DATA: list[BossData]


def _get_tier_treshold(cb_id: int) -> list[int]:
    data = _c.execute(
        f"SELECT phase from clan_battle_2_map_data where clan_battle_id={cb_id}"
    ).fetchall()
    tier_threshold: list[int] = []
    for (tier,) in set(data):
        (threshold,) = _c.execute(
            f"SELECT lap_num_from from clan_battle_2_map_data where clan_battle_id={cb_id} and phase={tier}"
        ).fetchall()[0]
        tier_threshold.append(threshold)
    tier_threshold.sort()
    return tier_threshold


def _get_bosses_data(cb_id: int, tier_threshold: list[int]) -> list[BossData]:
    boss_list: list[BossData] = []
    for lap_num in tier_threshold:
        phase, *tier_data = _c.execute(
            f"SELECT difficulty, wave_group_id_1, wave_group_id_2, wave_group_id_3, wave_group_id_4, wave_group_id_5  from clan_battle_2_map_data where clan_battle_id={cb_id} and lap_num_from={lap_num}"
        ).fetchone()
        boss_num = 1
        for wave_id in tier_data:
            boss_id = _c.execute(
                f"SELECT enemy_id_1 from wave_group_data where wave_group_id = {wave_id}"
            ).fetchone()[0]
            if phase == -2:
                unit_id, name, max_hp = _c.execute(
                    f"SELECT unit_id, name, hp from enemy_parameter where enemy_id = {boss_id}"
                ).fetchone()
                boss_list.append(
                    BossData(
                        NAME=name,
                        NUMBER=boss_num,
                        IMG_URL=f"https://redive.estertion.win/icon/unit/{unit_id}.webp",
                        MAX_HP_LIST=[max_hp],
                    )
                )
            else:
                max_hp = _c.execute(
                    f"SELECT hp from enemy_parameter where enemy_id = {boss_id}"
                ).fetchone()[0]
                boss_list[boss_num - 1].MAX_HP_LIST.append(max_hp)
            boss_num += 1
    return boss_list


def jst_time(minutes: int = 0, seconds: int = 0) -> datetime:
    utc_now = datetime.now(tz=pytz.timezone("UTC"))
    jst_now = utc_now.astimezone(pytz.timezone("Japan"))
    return jst_now + timedelta(minutes=minutes, seconds=seconds)


def _get_closest_cb_id() -> int:
    tz = pytz.timezone("Japan")
    now = jst_time()
    cb_schedules = _c.execute(
        "SELECT clan_battle_id, start_time from clan_battle_period"
    ).fetchall()
    return min(
        cb_schedules,
        key=lambda x: abs(
            (
                datetime.strptime(x[1], "%Y/%m/%d %H:%M:%S").replace(tzinfo=tz) - now
            ).total_seconds()
        ),
    )[0]


GC: gspread.Client | None
Drive: GoogleDrive
GC, DRIVE = connect_to_drive()

print("Downloading master.db")
_DB_URL = "https://github.com/lskyset/nozomi-cb-data/raw/main/master.db"
_DB_PATH = "volume/master.db"
urllib.request.urlretrieve(_DB_URL, _DB_PATH)

_conn = sqlite3.connect(_DB_PATH)
_c = _conn.cursor()

print("Loading clanbattle data.")
_CB_ID = _get_closest_cb_id()
_DB_START_DATE, _DB_END_DATE = _c.execute(
    f"SELECT start_time, end_time from clan_battle_period where clan_battle_id={_CB_ID}"
).fetchall()[-1]
_CB_TIER_THRESHOLD = _get_tier_treshold(_CB_ID)
_CB_BOSSES = _get_bosses_data(_CB_ID, _CB_TIER_THRESHOLD)

if BotConfig().BOT_ENV:
    _CB_START_DATE = jst_time(minutes=(-60 * 24))
    _CB_END_DATE = jst_time(minutes=(60 * 24 * 3 + 60 * 19 - 1), seconds=59)
else:
    tz = pytz.timezone("Japan")
    _CB_START_DATE = datetime.strptime(_DB_START_DATE, "%Y/%m/%d %H:%M:%S").replace(
        tzinfo=tz
    )
    _CB_END_DATE = datetime.strptime(_DB_END_DATE, "%Y/%m/%d %H:%M:%S").replace(
        tzinfo=tz
    )

CB_DATA: PricoCbData = PricoCbData(
    CB_ID=_CB_ID,
    TIER_THRESHOLD=_CB_TIER_THRESHOLD,
    START_DATE=_CB_START_DATE,
    END_DATE=_CB_END_DATE,
    BOSSES_DATA=_CB_BOSSES,
)

TIER_COLOURS: list[tuple[int, int, int]] = [
    (132, 189, 107),
    (112, 166, 225),
    (200, 109, 167),
    (206, 80, 68),
    (181, 105, 209),
]
