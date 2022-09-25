# import pytest
# import datetime
# from nozomi_cb_bot.config import ClanConfig, PricoCbData, BossData

# @pytest.fixture()
# def mock_BossData(boss_number: int = 1) -> BossData:
#     return BossData(
#         NAME=f"boss{boss_number}",
#         NUMBER=boss_number,
#         IMG_URL=f"{boss_number}.png",
#         MAX_HP_LIST=[boss_number] * 5,
#     )

# @pytest.fixture()
# def mock_ClanConfig(
#     name: str = "test",
#     guild_id: int = 0,
#     channel_id: int = 0,
#     clan_role_id: int = 0,
#     clan_mod_role_id: int = 0,
# ) -> ClanConfig:
#     return ClanConfig(
#         name=name,
#         GUILD_ID=guild_id,
#         CHANNEL_ID=channel_id,
#         CLAN_ROLE_ID=clan_role_id,
#         CLAN_MOD_ROLE_ID=clan_mod_role_id,
#     )

# @pytest.fixture()
# def mock_PricoCbData(
#     cb_id: int = 0,
#     tier_threshold: list | None = None,
#     start_date: datetime.datetime | None = None,
#     end_date: datetime.datetime | None = None,
#     bosses_data: list[BossData] | None = None,
# ) -> PricoCbData:
#     return PricoCbData(
#         CB_ID=cb_id,
#         TIER_THRESHOLD=tier_threshold or [1, 2, 3, 4, 5],
#         START_DATE=start_date or datetime.datetime(0, 0, 0),
#         END_DATE=end_date or datetime.datetime(0, 0, 0),
#         BOSSES_DATA=bosses_data or [mock_BossData(i) for i in range(5)],
#     )
