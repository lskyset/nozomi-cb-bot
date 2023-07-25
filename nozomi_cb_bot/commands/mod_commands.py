from discord.ext import commands

from nozomi_cb_bot import emoji
from nozomi_cb_bot.discord_ui import discord_ui
from nozomi_cb_bot.nozomi import Nozomi
from nozomi_cb_bot.response_messages import (
    ErrorMessage,
    HelpMessage,
    ResponseMessage,
    command_error_respond,
    command_success_respond,
)
from nozomi_cb_bot.utils.command_utils import NozoContext


class ModCommands(commands.Cog, name="Mod Commands"):  # type: ignore
    """Mod Commands are commands that can only be used by the clan's leader and sub-leaders."""

    def __init__(self, bot):
        self.bot: Nozomi = bot

    async def cog_check(self, ctx: NozoContext):
        clan = self.bot.clan_manager.find_clan_by_id(
            ctx.message.channel.guild.id, ctx.message.channel.id
        )
        if clan:
            ctx.clan = clan
            if any(
                ctx.author.get_role(role) for role in ctx.clan.config.CLAN_MOD_ROLE_IDS  # type: ignore
            ):
                return True
            if not ctx.message.content.startswith(f"{self.bot.command_prefix}help"):
                await command_error_respond(ctx, ErrorMessage.NOT_MOD)
        return False

    @commands.command()
    async def stop(self, ctx: NozoContext):
        """Stops the clan battle"""
        clan = self.bot.clan_manager.find_clan_by_id(
            ctx.message.channel.guild.id, ctx.message.channel.id
        )
        if clan:
            clan.save()
            clan._db.close()
            del self.bot.clan_manager.clans[self.bot.clan_manager.clans.index(clan)]
            await ctx.message.add_reaction(emoji.ok)

    @commands.command()
    async def shutdown(self, ctx):
        """Stops the bot"""
        for clan in self.bot.clan_manager.clans:
            clan.save()
            clan._db.close()
        await ctx.message.add_reaction(emoji.ok)
        await self.bot.close()

    @commands.command(aliases=("force_reset",))
    async def force_daily_reset(self, ctx: NozoContext):
        """ """
        daily_reset(ctx.bot.clan_manager.clans)

    @commands.command()
    async def imp(self, ctx: NozoContext, *args):
        """Impersonate someone else"""
        if not args:
            return await command_error_respond(ctx, ErrorMessage.NO_ARGS)
        if not ctx.message.mentions:
            return await command_error_respond(ctx, ErrorMessage.NO_MENTION)
        if ctx.message.mentions[0].mention != args[0]:
            return await command_error_respond(ctx, ErrorMessage.IMP)
        member = ctx.message.mentions[0]
        ctx.message.author = member
        ctx.message.content = " ".join(args[1:])
        await self.bot.process_commands(ctx.message)

    @commands.command()
    async def edit(self, ctx: NozoContext, *args):
        args = tuple(map(str.lower, args))
        if not args:
            return await command_error_respond(
                ctx, ErrorMessage.NO_ARGS, HelpMessage.EMPTY
            )
        ctx.boss = None
        for boss in ctx.clan.bosses:
            if f"b{boss.number}" in args[0]:
                ctx.boss = boss
        if ctx.boss is None:
            return await command_error_respond(
                ctx, ErrorMessage.NO_BOSS, HelpMessage.EMPTY
            )
        hp, wave, *_ = args[2:]
        ctx.boss._hp = int(hp)
        ctx.boss._wave = int(wave)
        ctx.boss._save()
        await discord_ui.update_ui(ctx.clan)

        return await command_success_respond(ctx, ResponseMessage.DONE)


def daily_reset(clans):
    for clan in clans:
        clan.daily_reset()


async def setup(bot: Nozomi):
    await bot.add_cog(ModCommands(bot))
