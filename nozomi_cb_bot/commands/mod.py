from discord.ext import commands

from .. import emoji as e
from ..config import BotConfig

P = BotConfig().PREFIX


class Mod_commands(commands.Cog, name="Mod Commands"):  # type: ignore
    """Mod Commands are commands that can only be used by the clan's leader and sub-leaders."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        clan = self.bot.clan_manager.find_clan_by_id(
            ctx.message.channel.guild.id, ctx.message.channel.id
        )
        if ctx.author.id in clan.mods:
            return True
        if not ctx.message.content.startswith(f"{P}help"):
            await ctx.send(
                f"You dont have the permission to use this command {ctx.author.mention}",
                delete_after=5,
            )
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
                await ctx.message.add_reaction(e.ok)
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
                        f"Argument not found {ctx.author.mention}\nUse for example `{P}fdq @Nozomi b1` to unqueue Nozomi from b1's queue",
                        delete_after=5,
                    )

    @commands.command()
    async def stop(self, ctx):
        """Stops the clan battle"""
        clan = self.bot.clan_manager.find_clan_by_id(
            ctx.message.channel.guild.id, ctx.message.channel.id
        )
        clan.drive_update()
        clan.conn.close()
        del self.bot.clans[self.bot.clans.index(clan)]
        await ctx.message.add_reaction(e.ok)

    @commands.command()
    async def shutdown(self, ctx):
        """Stops the bot"""
        for clan in self.bot.clans:
            clan.drive_update()
            clan.conn.close()
        await ctx.message.add_reaction(e.ok)
        await self.bot.close()

    @commands.command(aliases=("force_reset",))
    async def force_daily_reset(self, ctx):
        """ """
        daily_reset(self.bot.clans)

    @commands.command()
    async def imp(self, ctx, *args):
        """ Impersonate someone else """
        if ctx.message.mentions:
            member = ctx.message.mentions[0]
            clan = self.bot.clan_manager.find_clan_by_id(
                ctx.message.channel.guild.id, ctx.message.channel.id
            )
            if clan:
                message = ctx.message
                message.author = member
                message.content = " ".join(message.content.split(" ")[2:])
                await self.bot.process_commands(message)


def daily_reset(clans):
    for clan in clans:
        clan.daily_reset()
