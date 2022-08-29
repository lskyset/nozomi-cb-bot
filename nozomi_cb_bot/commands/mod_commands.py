from discord.ext import commands

from nozomi_cb_bot import cb, emoji
from nozomi_cb_bot.nozomi import Nozomi
from nozomi_cb_bot.response_messages import ErrorMessage, command_error_respond


class ModCommands(commands.Cog, name="Mod Commands"):  # type: ignore
    """Mod Commands are commands that can only be used by the clan's leader and sub-leaders."""

    def __init__(self, bot):
        self.bot: Nozomi = bot

    async def cog_check(self, ctx):
        ctx.clan = cb.Clan = self.bot.clan_manager.find_clan_by_id(
            ctx.message.channel.guild.id, ctx.message.channel.id
        )
        if ctx.clan:
            if ctx.author.get_role(ctx.clan.config.CLAN_MOD_ROLE_ID):
                return True
            if not ctx.message.content.startswith(f"{self.bot.command_prefix}help"):
                await command_error_respond(ctx, ErrorMessage.NOT_MOD)
        return False

    @commands.command(aliases=("fc",))
    async def force_cancel(self, ctx):
        """ """
        if ctx.message.mentions:
            member = ctx.message.mentions[0]
            clan = self.bot.clan_manager.find_clan_by_id(
                ctx.message.channel.guild.id, ctx.message.channel.id
            )
            if clan:
                boss = clan.cancel_hit(member.id, ctx.message)
                await ctx.message.add_reaction(emoji.ok)
                await clan.ui.update(boss.message_id)

    @commands.command(aliases=("fdq",))
    async def force_dequeue(self, ctx, *args):
        """ """
        args = tuple(map(str.lower, args))
        if ctx.message.mentions:
            member = ctx.message.mentions[0]
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
                    clan.dequeue(member.id, boss_message)
                    await clan.ui.update(boss.message_id)
                else:
                    await ctx.send(
                        f"Argument not found {ctx.author.mention}\nUse for example `{self.bot.command_prefix}fdq @Nozomi b1` to unqueue Nozomi from b1's queue",
                        delete_after=5,
                    )

    @commands.command()
    async def stop(self, ctx):
        """Stops the clan battle"""
        clan = self.bot.clan_manager.find_clan_by_id(
            ctx.message.channel.guild.id, ctx.message.channel.id
        )
        clan.save()
        clan._db._conn.close()
        del self.bot.clans[self.bot.clans.index(clan)]
        await ctx.message.add_reaction(emoji.ok)

    @commands.command()
    async def shutdown(self, ctx):
        """Stops the bot"""
        for clan in self.bot.clans:
            clan.save()
            clan._db._conn.close()
        await ctx.message.add_reaction(emoji.ok)
        await self.bot.close()

    @commands.command(aliases=("force_reset",))
    async def force_daily_reset(self, ctx):
        """ """
        daily_reset(ctx.bot.clan_manager.clans)

    @commands.command()
    async def imp(self, ctx: commands.Context, *args):
        """ Impersonate someone else """
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


def daily_reset(clans):
    for clan in clans:
        clan.daily_reset()


async def setup(bot: Nozomi):
    await bot.add_cog(ModCommands(bot))
