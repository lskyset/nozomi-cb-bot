from itertools import zip_longest
from typing import cast

import discord
from discord.ext import commands

from nozomi_cb_bot.cb import Boss, Clan

from .embeds import BossEmbed, OverviewEmbed
from .views import BossView, OverviewView


async def start_ui(bot: commands.Bot, channel: discord.TextChannel, clan: Clan):
    for boss in clan.bosses:
        if not boss.message_id:
            boss.message = await channel.send(f"Loading b{boss.number}...")
        await resolve_boss(boss, channel)
    if not clan.overview_message_id:
        clan.overview_message = await channel.send("Loading overview...")
    await resolve_overview(clan, channel)

    await update_ui(clan, channel)
    await init_views(bot, clan)


async def resolve_overview(clan: Clan, channel: discord.TextChannel) -> None:
    if clan.overview_message is None and clan.overview_message_id is not None:
        clan.overview_message = await channel.fetch_message(clan.overview_message_id)


async def resolve_boss(boss: Boss, channel: discord.TextChannel) -> None:
    if boss.message is None and boss.message_id is not None:
        boss.message = await channel.fetch_message(boss.message_id)


async def init_views(bot: commands.Bot, clan: Clan):
    print(f"Loading {clan.config.name}'s views.")
    for boss in clan.bosses:
        bot.add_view(BossView(boss), message_id=boss.message_id)
    bot.add_view(OverviewView(clan), message_id=clan.overview_message_id)


async def update_ui(clan: Clan, channel: discord.TextChannel | None = None):
    for boss in clan.bosses:
        await update_boss_message(boss, channel=channel)
    await update_overview_message(clan, channel)


async def update_boss_message(
    boss: Boss,
    channel: discord.TextChannel | None = None,
) -> None:
    if channel is not None:
        await resolve_boss(boss, channel)
    if boss.message is None:
        return
    new_boss_embed = BossEmbed(boss)
    boss_view = BossView(boss)
    if not compare_embeds(boss.message.embeds, [new_boss_embed]):
        if boss.message.guild is not None and boss.message.channel is not None:
            boss.message.channel = cast(discord.TextChannel, boss.message.channel)
            print(
                f'Updating B{boss.number} in "{boss.message.guild.name}" #{boss.message.channel.name}'
            )
            boss.message = await boss.message.edit(
                content=None, embed=new_boss_embed, view=boss_view
            )


async def update_overview_message(
    clan: Clan,
    channel: discord.TextChannel | None = None,
) -> None:
    if channel is not None:
        await resolve_overview(clan, channel)
    if clan.overview_message is None:
        return
    new_overview_embed = OverviewEmbed(clan)
    overview_view = OverviewView(clan)
    if not compare_embeds(clan.overview_message.embeds, [new_overview_embed]):
        if (
            clan.overview_message.guild is not None
            and clan.overview_message.channel is not None
        ):
            clan.overview_message.channel = cast(
                discord.TextChannel, clan.overview_message.channel
            )
            print(
                f'Updating Overview in "{clan.overview_message.guild.name}" #{clan.overview_message.channel.name}'
            )
            clan.overview_message = await clan.overview_message.edit(
                content=None, embed=new_overview_embed, view=overview_view
            )


def compare_embeds(
    message_embeds: list[discord.Embed], new_embeds: list[discord.Embed]
) -> bool:
    for old, new in zip_longest(message_embeds, new_embeds, fillvalue=None):
        if not (
            old
            and new
            and all(
                (
                    old.description == new.description,
                    old.title == new.title,
                    old.footer.text == new.footer.text,
                    old.footer.icon_url == new.footer.icon_url,
                    old.image.url == new.image.url,
                    old.colour == new.colour,
                    compare_embed_fields(old.fields, new.fields),
                )
            )
        ):
            return False
    return True


def compare_embed_fields(
    old_fields: list[discord.Embed], new_fields: list[discord.Embed]
):
    for old, new in zip_longest(old_fields, new_fields, fillvalue=None):
        if not (
            old
            and new
            and all(
                (
                    old.name == new.name,
                    old.value == new.value,
                )
            )
        ):
            return False
    return True
