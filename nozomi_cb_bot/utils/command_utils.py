from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from nozomi_cb_bot.cb import Boss, Clan, Member
    from nozomi_cb_bot.discord_ui.views import DoneView


@dataclass
class NozoContext(commands.Context):
    clan: Clan
    clan_member: Member
    syncing_member: Member | None
    boss: Boss | None
    edit_original_response: bool
    new_view: DoneView | None


async def proxy_command(interaction: discord.Interaction, message_content: str) -> None:
    await interaction.response.defer(ephemeral=True)
    client: commands.Bot = interaction.client  # type: ignore
    ctx = await client.get_context(interaction)
    ctx.message.content = message_content
    ctx.message.interaction = interaction  # type: ignore
    await client.process_commands(ctx.message)


async def proxy_imp_command(
    interaction: discord.Interaction,
    message_content: str,
    member: discord.Member,
) -> None:
    await interaction.response.defer(ephemeral=True)
    client: commands.Bot = interaction.client  # type: ignore
    ctx = await client.get_context(interaction)
    ctx.message.author = member
    ctx.message.content = message_content
    ctx.message.interaction = interaction  # type: ignore
    await client.process_commands(ctx.message)
