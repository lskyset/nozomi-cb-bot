# TODO: move and modify to test clan_manager.find_clan_by_id

# from nozomi_cb_bot.commands import util


# def test_find_clan_midriff() -> None:
#     message = create_message(0, 0)
#     clans = create_test_clans()

#     found_clan = util.find_clan(message, clans)
#     assert found_clan == clans[0]


# def test_find_clan_thighs() -> None:
#     message = create_message(1, 1)
#     clans = create_test_clans()

#     found_clan = util.find_clan(message, clans)
#     assert found_clan == clans[1]


# def test_not_finding_clan_with_different_guild_id() -> None:
#     message = create_message(2, 0)
#     clans = create_test_clans()

#     found_clan = util.find_clan(message, clans)
#     assert found_clan is None


# def test_not_finding_clan_with_different_channel_id() -> None:
#     message = create_message(0, 2)
#     clans = create_test_clans()

#     found_clan = util.find_clan(message, clans)
#     assert found_clan is None


# def test_find_clan_in_one_entry_list():
#     successful_message = create_message(0, 0)
#     failed_message = create_message(1, 1)
#     clans = create_test_clans()[0:1]

#     successful_clan = util.find_clan(successful_message, clans)
#     assert successful_clan == clans[0]
#     failed_clan = util.find_clan(failed_message, clans)
#     assert failed_clan is None


# def create_test_clans():
#     midriff = create_clan(0, 0)
#     thighs = create_clan(1, 1)
#     return [midriff, thighs]


# def create_clan(guild_id, channel_id):
#     clan = Object()
#     clan.guild_id = guild_id
#     clan.channel_id = channel_id
#     return clan


# def create_message(guild_id, channel_id):
#     message = Object()
#     message.channel = Object()
#     message.channel.id = channel_id
#     message.guild = Object()
#     message.guild.id = guild_id
#     return message


# class Object(object):
#     pass
