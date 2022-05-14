from discord.ext import commands, tasks

from .. import config as cfg
from .. import emoji as e
from ..config import CB_DATA, BotConfig

P = BotConfig().PREFIX


class Cb_commands(commands.Cog, name="CB Commands"):  # type: ignore
    """CB Commands are commands that can be used in a channel where a clan battle database has been loaded."""

    def __init__(self, bot):
        self.bot = bot
        self.ui_update_loop.start()

    async def cog_check(self, ctx):
        return True

    def cog_unload(self):
        self.ui_update_loop.cancel()

    @commands.command()
    async def of(self, ctx):
        """ """
        clan = self.bot.clan_manager.find_clan_by_id(
            ctx.message.channel.guild.id, ctx.message.channel.id
        )
        if clan:
            member = clan.find_member(ctx.author.id)
            if member:
                member.of_status = True
                await ctx.message.add_reaction(e.ok)

    @commands.command()
    async def rmof(self, ctx):
        """ """
        clan = self.bot.clan_manager.find_clan_by_id(
            ctx.message.channel.guild.id, ctx.message.channel.id
        )
        if clan:
            member = clan.find_member(ctx.author.id)
            if member:
                member.of_status = False
                await ctx.message.add_reaction(e.ok)

    @commands.command(aliases=("q", "que"))
    async def queue(self, ctx, *args, from_button=False):
        """ """
        args = tuple(map(str.lower, args))
        clan = self.bot.clan_manager.find_clan_by_id(
            ctx.message.channel.guild.id, ctx.message.channel.id
        )
        if clan:
            boss_message = None
            if from_button:
                boss_message = ctx.message
            else:
                for boss in clan.bosses:
                    if f"b{boss.number}" in args:
                        boss_message = await ctx.channel.fetch_message(boss.message_id)
                        boss_message.author = ctx.author
                        break

            if boss_message:
                await clan.queue(ctx.author.id, boss_message, *args)
                await clan.ui.update(boss_message.id)
            else:
                if args:
                    await ctx.send(
                        f"Boss not found {ctx.author.mention}\nUse for example `{P}q b1` to queue for b1",
                        delete_after=7,
                    )
                else:
                    await ctx.send(
                        f"Argument not found {ctx.author.mention}\nUse for example `{P}q b1` to queue for b1",
                        delete_after=7,
                    )

    @commands.command(aliases=("dq", "dque"))
    async def dequeue(self, ctx, *args):
        """ """
        args = tuple(map(str.lower, args))
        clan = self.bot.clan_manager.find_clan_by_id(
            ctx.message.channel.guild.id, ctx.message.channel.id
        )
        if clan:
            boss_message = None
            for boss in clan.bosses:
                if f"b{boss.number}" in args:
                    boss_message = await ctx.channel.fetch_message(boss.message_id)
                    boss_message.author = ctx.author
                    break
            if boss_message:
                clan.dequeue(ctx.author.id, boss_message)
                await clan.ui.update(boss.message_id)
            else:
                await ctx.send(
                    f"Argument not found {ctx.author.mention}\nUse for example `{P}dq b1` to unqueue yourself from b1's queue",
                    delete_after=7,
                )

    @commands.command(aliases=("h", "hitting"))
    async def hit(self, ctx, *args, from_button=False):
        """ """
        args = tuple(map(str.lower, args))
        clan = self.bot.clan_manager.find_clan_by_id(
            ctx.message.channel.guild.id, ctx.message.channel.id
        )
        if clan:
            boss_message = None
            if from_button:
                boss_message = ctx.message
            else:
                for boss in clan.bosses:
                    if f"b{boss.number}" in args:
                        boss_message = await ctx.channel.fetch_message(boss.message_id)
                        boss_message.author = ctx.author
                        break
            if boss_message:
                await clan.hitting(ctx.author.id, boss_message, *args)
                await clan.ui.update(boss_message.id)
            else:
                if args:
                    await ctx.send(
                        f"Boss not found {ctx.author.mention}\nUse for example `{P}h b1` to hit b1",
                        delete_after=7,
                    )
                else:
                    await ctx.send(
                        f"Argument not found {ctx.author.mention}\nUse for example `{P}h b1` to hit b1",
                        delete_after=7,
                    )

    @commands.command(aliases=("s", "syncing"))
    async def sync(self, ctx, *args):
        """ """
        args = tuple(map(str.lower, args))
        if ctx.message.mentions:
            sync_member = ctx.message.mentions[0]
            if sync_member == ctx.author:
                await ctx.send(
                    f"You can't sync with yourself {ctx.author.mention}", delete_after=5
                )
                return
            clan = self.bot.clan_manager.find_clan_by_id(
                ctx.message.channel.guild.id, ctx.message.channel.id
            )
            if clan:
                boss_message = None
                hit_member = clan.find_member(ctx.author.id)
                if hit_member.hitting_boss_number:
                    boss_message = await ctx.channel.fetch_message(
                        clan.bosses[hit_member.hitting_boss_number - 1].message_id
                    )
                    boss_message.author = ctx.author
                else:
                    for boss in clan.bosses:
                        if f"b{boss.number}" in args:
                            boss_message = await ctx.channel.fetch_message(
                                boss.message_id
                            )
                            boss_message.author = ctx.author
                            break
                if boss_message:
                    await clan.syncing(
                        ctx.author.id, sync_member.id, boss_message, *args
                    )
                    await clan.ui.update(boss_message.id)
                else:
                    await ctx.send(
                        f"Boss not found {ctx.author.mention}\nUse for example `{P}s b1 @Nozomi` to hit b1 with Nozomi",
                        delete_after=5,
                    )
        else:
            await ctx.send(
                f"You need to mention the person syncing with you {ctx.author.mention}",
                delete_after=5,
            )

    @commands.command(aliases=("c",))
    async def cancel(self, ctx):
        """ """
        clan = self.bot.clan_manager.find_clan_by_id(
            ctx.message.channel.guild.id, ctx.message.channel.id
        )
        if clan:
            boss = clan.cancel_hit(ctx.message.author.id)
            await clan.ui.update(boss.message_id)

    @commands.command(aliases=("d",))
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.member)
    async def done(self, ctx, *args):
        """ """
        if (cfg.jst_time() - CB_DATA.START_DATE).total_seconds() < 0:
            await ctx.send(
                f"CB hasn't started yet {ctx.author.mention}", delete_after=5
            )
            return
        args = tuple(map(str.lower, args))
        clan = self.bot.clan_manager.find_clan_by_id(
            ctx.message.channel.guild.id, ctx.message.channel.id
        )
        if clan:
            boss_message_id = await clan.done(ctx.message.author.id, ctx.message, *args)
            self.bot.get_command("done").reset_cooldown(ctx)
            await clan.ui.update(boss_message_id)

    @commands.command()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.member)
    async def dead(self, ctx, *args):
        """ """
        args = (str(10 ** 9 - 1), *args)
        await self.done(ctx, *args)
        self.bot.get_command("dead").reset_cooldown(ctx)

    @commands.command()
    async def undo(self, ctx):
        """ """
        clan = self.bot.clan_manager.find_clan_by_id(
            ctx.message.channel.guild.id, ctx.message.channel.id
        )
        if clan:
            boss = clan.undo(ctx.message)
            if boss:
                await ctx.message.add_reaction(e.ok)
                await clan.ui.update(boss.message_id)

    @tasks.loop(seconds=20)
    async def ui_update_loop(self):
        for clan in self.bot.clan_manager.clans:
            if clan.is_daily_reset:
                clan.daily_reset()
                clan.is_daily_reset = False

            guild = self.bot.get_guild(clan.guild_id)
            channel = guild.get_channel(clan.channel_id)
            if self.ui_update_loop.current_loop % 150 == 0:
                await channel.send("Reloading messages, please wait", delete_after=10)
                await clan.ui.start(channel, clan)
            else:
                for boss in clan.bosses:
                    if boss.hitting_member_id == 0 and boss.queue_timeout:
                        message = channel.get_partial_message(boss.message_id)
                        if clan.timeout_minutes > 0:
                            clan.check_queue(message)
                        await clan.ui.update(boss.message_id)
