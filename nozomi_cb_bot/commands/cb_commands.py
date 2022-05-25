from discord.ext import commands, tasks  # type: ignore

from nozomi_cb_bot import emoji
from nozomi_cb_bot.discord_ui import discord_ui
from nozomi_cb_bot.discord_ui.views import DoneView
from nozomi_cb_bot.nozomi import Nozomi
from nozomi_cb_bot.response_messages import (
    ErrorMessage,
    HelpMessage,
    ResponseMessage,
    command_error_respond,
    command_success_respond,
)


class CbCommands(commands.Cog, name="CB Commands"):  # type: ignore
    """CB Commands are commands that can be used in a channel where a clan battle database has been loaded."""

    def __init__(self, bot: Nozomi):
        self.bot = bot
        # self.ui_update_loop.start()

    async def cog_check(self, ctx: commands.Context) -> bool:
        ctx.clan = self.bot.clan_manager.find_clan_by_id(
            ctx.message.channel.guild.id, ctx.message.channel.id
        )
        if ctx.clan:
            ctx.new_view = None
            ctx.edit_original_message = False
            ctx.bot = self.bot
            ctx.boss = None
            ctx.clan_member = ctx.clan.find_member(ctx.message.author.id)
            return ctx.clan_member is not None
        return False

    async def cog_after_invoke(self, ctx: commands.Context) -> None:
        await discord_ui.update_ui(ctx.clan)

    def cog_unload(self):
        self.ui_update_loop.cancel()

    @commands.command()
    async def of(self, ctx):
        """ """
        ctx.clan_member.of_status = True
        await ctx.message.add_reaction(emoji.ok)

    @commands.command()
    async def rmof(self, ctx):
        """ """
        ctx.clan_member.of_status = False
        await ctx.message.add_reaction(emoji.ok)

    @commands.command(aliases=("q", "que"))
    async def queue(self, ctx: commands.Context, *args):
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
    async def dequeue(self, ctx: commands.Context, *args):
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
    async def hit(self, ctx: commands.Context, *args):
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

        if error := ctx.clan.hitting(ctx.clan_member, ctx.boss, *args):
            return await command_error_respond(ctx, error)

        ctx.new_view = DoneView(ctx.boss)
        return await command_success_respond(ctx, ResponseMessage.HIT)

    @commands.command(aliases=("s", "syncing"))
    async def sync(self, ctx: commands.Context, *args):
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
        if boss is None:
            return await command_error_respond(
                ctx, ErrorMessage.NO_BOSS, HelpMessage.SYNC
            )
        result = ctx.clan.syncing(ctx.clan_member, ctx.syncing_member, ctx.boss, *args)
        if isinstance(result, ErrorMessage):
            return await command_error_respond(ctx, result)
        ctx.new_view = DoneView(ctx.boss)
        return await command_success_respond(ctx, ResponseMessage.HIT, result)

    @commands.command(aliases=("c",))
    async def cancel(self, ctx: commands.Context):
        """ """
        ctx.boss = ctx.clan.cancel_hit(ctx.clan_member)
        ctx.edit_original_message = True
        if ctx.boss is None:
            return await command_error_respond(ctx, ErrorMessage.CANCEL)
        return await command_success_respond(ctx, ResponseMessage.CANCEL)

    @commands.command(aliases=("d",))
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.member)
    async def done(self, ctx: commands.Context, *args):
        """ """
        # if (cfg.jst_time() - CB_DATA.START_DATE).total_seconds() < 0:
        #     await ctx.send(
        #         f"CB hasn't started yet {ctx.author.mention}", delete_after=ctx.delete_after
        #     )
        #     return
        args = tuple(map(str.lower, args))
        result = ctx.clan.done(ctx.clan_member, *args)
        ctx.edit_original_message = True
        if isinstance(result, ErrorMessage):
            return await command_error_respond(ctx, result, HelpMessage.DONE)
        await command_success_respond(ctx, ResponseMessage.DONE, result)
        self.bot.get_command("done").reset_cooldown(ctx)

    @commands.command()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.member)
    async def dead(self, ctx: commands.Context, *args):
        """ """
        args = (str(10 ** 9 - 1), *args)
        await self.done(ctx, *args)
        self.bot.get_command("dead").reset_cooldown(ctx)

    @commands.command()
    async def undo(self, ctx: commands.Context):
        """ """
        ctx.boss = await ctx.clan.undo(ctx.message)
        if ctx.boss:
            await ctx.message.add_reaction(emoji.ok)

    @tasks.loop(seconds=20)
    async def ui_update_loop(self):
        pass
        # for clan in self.bot.clan_manager.clans:
        #     if clan.is_daily_reset:
        #         clan.daily_reset()
        #         clan.is_daily_reset = False

        #     guild = self.bot.get_guild(clan.guild_id)
        #     channel = guild.get_channel(clan.channel_id)
        #     if self.ui_update_loop.current_loop % 150 == 0:
        #         await channel.send("Reloading messages, please wait", delete_after=10)
        #         await clan.ui.start(channel, clan)
        #     else:
        #         for boss in clan.bosses:
        #             if boss.hitting_member_id == 0 and boss.queue_timeout:
        #                 message = channel.get_partial_message(boss.message_id)
        #                 if clan.timeout_minutes > 0:
        #                     clan.check_queue(message)
        #                 await clan.ui.update(boss.message_id)


async def setup(bot: Nozomi):
    await bot.add_cog(CbCommands(bot))
