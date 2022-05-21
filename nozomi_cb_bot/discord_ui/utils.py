from typing import cast

import discord
from discord.ext import commands


async def proxy_command(interaction: discord.Interaction, message_content: str) -> None:
    await interaction.response.defer()
    if interaction.message is not None:
        interaction.message.author = interaction.user
        interaction.message.content = message_content
        interaction.message.interaction = cast(discord.MessageInteraction, interaction)
        client: commands.Bot = interaction.client
        await client.process_commands(interaction.message)
