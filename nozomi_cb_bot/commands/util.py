def find_clan(message, clans):
    for clan in clans:
        if clan.guild_id == message.guild.id and clan.channel_id == message.channel.id:
            return clan
    return None
