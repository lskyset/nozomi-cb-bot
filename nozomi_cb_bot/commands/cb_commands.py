from discord.ext import commands

from nozomi_cb_bot.discord_ui import discord_ui
from nozomi_cb_bot.discord_ui.views import DoneView
from nozomi_cb_bot.nozomi import Nozomi
from nozomi_cb_bot.response_messages import (
    ErrorMessage,
    HelpMessage,
    ResponseMessage,
    command_error_respond,
    command_success_respond,
    command_success_respond_emoji,
)
from nozomi_cb_bot.utils.command_utils import NozoContext


class CbCommands(commands.Cog, name="CB Commands"):  # type: ignore
    """CB Commands are commands that can be used in a channel where a clan battle database has been loaded."""

    def __init__(self, bot: Nozomi):
        self.bot = bot

    async def cog_check(self, ctx: NozoContext) -> bool:
        if ctx.message.channel.guild is None:
            return False
        if clan := self.bot.clan_manager.find_clan_by_id(
            ctx.message.channel.guild.id, ctx.message.channel.id
        ):
            ctx.clan = clan
            ctx.new_view = None
            ctx.edit_original_response = False
            ctx.bot = self.bot
            ctx.boss = None
            if member := ctx.clan.find_member(ctx.message.author.id):
                ctx.clan_member = member
                return True
        return False

    async def cog_after_invoke(self, ctx: NozoContext) -> None:
        if ctx.clan is not None:
            await discord_ui.update_ui(ctx.clan)

    @commands.command()
    async def of(self, ctx):
        """ """
        ctx.clan_member.of_status = True
        await command_success_respond_emoji(ctx)

    @commands.command()
    async def rmof(self, ctx):
        """ """
        ctx.clan_member.of_status = False
        await command_success_respond_emoji(ctx)

    @commands.command(aliases=("q", "que"))
    async def queue(self, ctx: NozoContext, *args):
        """ """
        args = tuple(map(str.lower, args))
        if not args:
            return await command_error_respond(
                ctx, ErrorMessage.NO_ARGS, HelpMessage.QUEUE
            )
        for boss in ctx.clan.bosses:
            if f"b{boss.number}" in args:
                ctx.boss = boss
        if ctx.boss is None:
            return await command_error_respond(
                ctx, ErrorMessage.NO_BOSS, HelpMessage.QUEUE
            )

        if error := ctx.clan.queue(ctx.clan_member, ctx.boss, *args):
            return await command_error_respond(ctx, error)

    @commands.command(aliases=("dq", "dque"))
    async def dequeue(self, ctx: NozoContext, *args):
        """ """
        args = tuple(map(str.lower, args))
        if not args:
            return await command_error_respond(
                ctx, ErrorMessage.NO_ARGS, HelpMessage.DEQUEUE
            )

        for boss in ctx.clan.bosses:
            if f"b{boss.number}" in args:
                ctx.boss = boss
        if ctx.boss is None:
            return await command_error_respond(
                ctx, ErrorMessage.NO_BOSS, HelpMessage.DEQUEUE
            )

        if error := ctx.clan.dequeue(ctx.clan_member, ctx.boss):
            return await command_error_respond(ctx, error)

    @commands.command(aliases=("h", "hitting"))
    async def hit(self, ctx: NozoContext, *args):
        """ """
        args = tuple(map(str.lower, args))
        if not args:
            return await command_error_respond(
                ctx, ErrorMessage.NO_ARGS, HelpMessage.HIT
            )

        for boss in ctx.clan.bosses:
            if f"b{boss.number}" in args:
                ctx.boss = boss
        if ctx.boss is None:
            return await command_error_respond(
                ctx, ErrorMessage.NO_BOSS, HelpMessage.HIT
            )

        result = ctx.clan.hitting(ctx.clan_member, ctx.boss, *args)
        if isinstance(result, ErrorMessage):
            return await command_error_respond(ctx, result)

        ctx.new_view = DoneView(ctx.boss)
        return await command_success_respond(ctx, ResponseMessage.HIT)

    @commands.command(aliases=("s", "syncing"))
    async def sync(self, ctx: NozoContext, *args):
        """ """
        args = tuple(map(str.lower, args))
        if not args:
            return await command_error_respond(
                ctx, ErrorMessage.NO_ARGS, HelpMessage.SYNC
            )
        if not ctx.message.mentions:
            return await command_error_respond(
                ctx, ErrorMessage.NO_MENTION, HelpMessage.SYNC_MENTION
            )

        ctx.syncing_member = ctx.clan.find_member(ctx.message.mentions[0].id)
        if ctx.syncing_member is None:
            return await command_error_respond(ctx, ErrorMessage.NO_SYNC_FOUND)
        if ctx.syncing_member == ctx.clan_member:
            return await command_error_respond(ctx, ErrorMessage.SELF_SYNC)

        if ctx.clan_member.hitting_boss_number:
            ctx.boss = ctx.clan.find_boss(
                boss_number=ctx.clan_member.hitting_boss_number
            )
        else:
            for boss in ctx.clan.bosses:
                if f"b{boss.number}" in args:
                    ctx.boss = boss
        if ctx.boss is None:
            return await command_error_respond(
                ctx, ErrorMessage.NO_BOSS, HelpMessage.SYNC
            )
        result = ctx.clan.syncing(ctx.clan_member, ctx.syncing_member, ctx.boss, *args)
        if isinstance(result, ErrorMessage):
            return await command_error_respond(ctx, result)
        ctx.new_view = DoneView(ctx.boss)
        return await command_success_respond(ctx, ResponseMessage.HIT, result)

    @commands.command(aliases=("c",))
    async def cancel(self, ctx: NozoContext):
        """ """
        ctx.boss = ctx.clan.cancel_hit(ctx.clan_member)
        ctx.edit_original_response = True
        if ctx.boss is None:
            return await command_error_respond(ctx, ErrorMessage.CANCEL)
        return await command_success_respond(ctx, ResponseMessage.CANCEL)

    @commands.command(aliases=("d",))
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.member)
    async def done(self, ctx: NozoContext, *args):
        """ """
        args = tuple(map(str.lower, args))
        result = ctx.clan.done(ctx.clan_member, *args)
        ctx.edit_original_response = True
        if isinstance(result, ErrorMessage):
            return await command_error_respond(ctx, result, HelpMessage.DONE)
        await command_success_respond(ctx, ResponseMessage.DONE, result)
        if command := self.bot.get_command("done"):
            command.reset_cooldown(ctx)

    @commands.command()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.member)
    async def dead(self, ctx: NozoContext, *args):
        """ """
        args = (str(10 ** 9 - 1), *args)
        await self.done(ctx, *args)
        if command := self.bot.get_command("dead"):
            command.reset_cooldown(ctx)

    @commands.command()
    async def undo(self, ctx: NozoContext):
        """ """
        ctx.boss = await ctx.clan.undo(ctx.message)
        if ctx.boss:
            await command_success_respond_emoji(ctx)


async def setup(bot: Nozomi):
    await bot.add_cog(CbCommands(bot))
