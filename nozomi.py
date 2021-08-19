import datetime
import os
import time

import discord
import pytz
from discord.ext import commands, tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

import db
import config as cfg
from config import PREFIX as P
import emoji as e
from ui import Ui


clans = []

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix=P, description="List of commands : (Under construction)", intents=intents, case_insensitive=True)
bot.help_command = commands.DefaultHelpCommand(dm_help=True, no_category='Other')


def find_clan(message):
    for clan in clans:
        if clan.guild_id == message.guild.id and clan.channel_id == message.channel.id:
            return clan
    return None


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}.\n')
    for cfg_clan_name, cfg_clan_data in cfg.CLANS.items():
        if cfg_clan_data['ENV'] == cfg.ENV and cfg_clan_name != 'default':
            channel = bot.get_channel(cfg_clan_data['CHANNEL_ID'])
            await cb_init(channel, cfg_clan_name, cfg_clan_data)


@bot.event
async def on_button_click(i: discord.Interaction, b: discord.ButtonClick):
    await i.defer()
    ctx = await bot.get_context(i.message)
    ctx.author = i.author
    ctx.message.author = i.author
    await ctx.invoke(bot.get_command(b.custom_id), from_button=True)


@bot.event
async def on_message(message):
    clan = find_clan(message)
    if clan:
        clan.log(message)
        if message.author.bot:
            return
        await message.delete(delay=3)
        await bot.process_commands(message)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.message.add_reaction(e.cross)


class Global_commands(commands.Cog, name='Global Commands'):
    """Global Commands are commands that can be used at any time"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    async def hello(self, ctx):
        """Says hello and mention the user (used for testing purposes)"""
        msg = f'Hello {ctx.author.mention}'
        await ctx.send(msg)


class Cb_commands(commands.Cog, name='CB Commands'):
    """CB Commands are commands that can be used in a channel where a clan battle database has been loaded."""
    def __init__(self, bot):
        self.bot = bot
        self.ui_update_loop.start()

    async def cog_check(self, ctx):  # check the cb date
        if (cfg.cb_end_date - cfg.jst_time()).total_seconds() < 0:
            await ctx.send(f'CB has ended {ctx.author.mention}', delete_after=5)
            return False
        if (cfg.jst_time() - cfg.cb_start_date).total_seconds() < 0:
            await ctx.send(f"CB hasn't started yet {ctx.author.mention}", delete_after=5)
            return False
        return True

    def cog_unload(self):
        self.ui_update_loop.cancel()

    @commands.command()
    async def of(self, ctx):
        """ """
        clan = find_clan(ctx.message)
        if clan:
            member = clan.find_member(ctx.author.id)
            if member:
                member.of_status = True
                await ctx.message.add_reaction(e.ok)

    @commands.command()
    async def rmof(self, ctx):
        """ """
        clan = find_clan(ctx.message)
        if clan:
            member = clan.find_member(ctx.author.id)
            if member:
                member.of_status = False
                await ctx.message.add_reaction(e.ok)

    @commands.command(aliases=('q', 'que'))
    async def queue(self, ctx, *args, from_button=False):
        """ """
        clan = find_clan(ctx.message)
        if clan:
            boss_message = None
            if from_button:
                boss_message = ctx.message
            else:
                for boss in clan.bosses:
                    if f'b{boss.number}' in args:
                        boss_message = await ctx.channel.fetch_message(boss.message_id)
                        boss_message.author = ctx.author
                        break
            if boss_message:
                await clan.queue(ctx.author.id, boss_message, *args)
                await clan.ui.update(boss_message.id)
            else:
                if args:
                    await ctx.send(f"Boss not found {ctx.author.mention}\nUse for example `{P}q b1` to queue for b1", delete_after=7)
                else:
                    await ctx.send(f"Argument not found {ctx.author.mention}\nUse for example `{P}q b1` to queue for b1", delete_after=7)

    @commands.command(aliases=('dq', 'dque'))
    async def dequeue(self, ctx, *args):
        """ """
        clan = find_clan(ctx.message)
        if clan:
            boss_message = None
            for boss in clan.bosses:
                if f'b{boss.number}' in args:
                    boss_message = await ctx.channel.fetch_message(boss.message_id)
                    boss_message.author = ctx.author
                    break
            if boss_message:
                clan.dequeue(ctx.author.id, boss_message)
                await clan.ui.update(boss.message_id)
            else:
                await ctx.send(f"Argument not found {ctx.author.mention}\nUse for example `{P}dq b1` to unqueue yourself from b1's queue", delete_after=7)

    @commands.command(aliases=('h', 'hitting'))
    async def hit(self, ctx, *args, from_button=False):
        """ """
        clan = find_clan(ctx.message)
        if clan:
            boss_message = None
            if from_button:
                boss_message = ctx.message
            else:
                for boss in clan.bosses:
                    if f'b{boss.number}' in args:
                        boss_message = await ctx.channel.fetch_message(boss.message_id)
                        boss_message.author = ctx.author
                        break
            if boss_message:
                await clan.hitting(ctx.author.id, boss_message, *args)
                await clan.ui.update(boss_message.id)
            else:
                if args:
                    await ctx.send(f"Boss not found {ctx.author.mention}\nUse for example `{P}h b1` to hit b1", delete_after=7)
                else:
                    await ctx.send(f"Argument not found {ctx.author.mention}\nUse for example `{P}h b1` to hit b1", delete_after=7)

    @commands.command(aliases=('s', 'syncing'))
    async def sync(self, ctx, *args):
        """ """
        if ctx.message.mentions:
            sync_member = ctx.message.mentions[0]
            if sync_member == ctx.author:
                await ctx.send(f"You can't sync with yourself {ctx.author.mention}", delete_after=5)
                return
            clan = find_clan(ctx.message)
            if clan:
                boss_message = None
                hit_member = clan.find_member(ctx.author.id)
                if hit_member.hitting_boss_number:
                    boss_message = await ctx.channel.fetch_message(clan.bosses[hit_member.hitting_boss_number - 1].message_id)
                    boss_message.author = ctx.author
                else:
                    for boss in clan.bosses:
                        if (f'b{boss.number}' in args):
                            boss_message = await ctx.channel.fetch_message(boss.message_id)
                            boss_message.author = ctx.author
                            break
                if boss_message:
                    await clan.syncing(ctx.author.id, sync_member.id, boss_message, *args)
                    await clan.ui.update(boss_message.id)
                else:
                    await ctx.send(f"Boss not found {ctx.author.mention}\nUse for example `{P}s b1 @Nozomi` to hit b1 with Nozomi", delete_after=5)
        else:
            await ctx.send(f'You need to mention the person syncing with you {ctx.author.mention}', delete_after=5)

    @commands.command(aliases=('c',))
    async def cancel(self, ctx):
        """ """
        clan = find_clan(ctx.message)
        if clan:
            boss = clan.cancel_hit(ctx.message.author.id, ctx.message)
            await clan.ui.update(boss.message_id)

    @commands.command(aliases=('d',))
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.member)
    async def done(self, ctx, *args):
        """ """
        clan = find_clan(ctx.message)
        if clan:
            boss_message_id = await clan.done(ctx.message.author.id, ctx.message, *args)
            bot.get_command('done').reset_cooldown(ctx)
            await clan.ui.update(boss_message_id)

    @commands.command()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.member)
    async def dead(self, ctx, *args):
        """ """
        args = ((str(10 ** 9 - 1), *args))
        await self.done(ctx, *args)
        bot.get_command('dead').reset_cooldown(ctx)

    @commands.command()
    async def undo(self, ctx):
        """ """
        clan = find_clan(ctx.message)
        if clan:
            boss = clan.undo(ctx.message)
            if boss:
                await ctx.message.add_reaction(e.ok)
            await clan.ui.update(boss.message_id)

    @tasks.loop(seconds=20)
    async def ui_update_loop(self):
        for clan in clans:
            if clan.is_daily_reset:
                clan.daily_reset()
                clan.is_daily_reset = False
            for boss in clan.bosses:
                if boss.hitting_member_id == 0 and boss.queue_timeout:
                    guild = bot.get_guild(clan.guild_id)
                    channel = guild.get_channel(clan.channel_id)
                    message = channel.get_partial_message(boss.message_id)
                    if clan.timeout_minutes > 0:
                        clan.check_queue(message)
                    await clan.ui.update(boss.message_id)


class Mod_commands(commands.Cog, name='Mod Commands'):
    """Mod Commands are commands that can only be used by the clan's leader and sub-leaders."""
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        clan = find_clan(ctx.message)
        if ctx.author.id in clan.mods:
            return True
        if not ctx.message.content.startswith(f'{P}help'):
            await ctx.send(f'You dont have the permission to use this command {ctx.author.mention}', delete_after=5)
        return False

    # @commands.command(brief='Start a clan battle.')
    # async def init(self, ctx, name='cb'):
    #     """Create a clan battle database and start a clan battle in the channel the command was used."""

    @commands.command(aliases=('fc',))
    async def force_cancel(self, ctx):
        """ """
        if ctx.message.mentions:
            member = ctx.message.mentions[0]
            clan = find_clan(ctx.message)
            if clan:
                boss = clan.cancel_hit(member.id, ctx.message)
                await ctx.message.add_reaction(e.ok)
                await clan.ui.update(boss.message_id)

    @commands.command(aliases=('fdq',))
    async def force_dequeue(self, ctx, *args):
        """ """
        if ctx.message.mentions:
            member = ctx.message.mentions[0]
            clan = find_clan(ctx.message)
            if clan:
                boss_message = None
                for boss in clan.bosses:
                    if f'b{boss.number}' in args:
                        boss_message = await ctx.channel.fetch_message(boss.message_id)
                        boss_message.author = ctx.author
                        break
                if boss_message:
                    clan.dequeue(member.id, boss_message)
                    await clan.ui.update(boss.message_id)
                else:
                    await ctx.send(f"Argument not found {ctx.author.mention}\nUse for example `{P}fdq @Nozomi b1` to unqueue Nozomi from b1's queue", delete_after=5)

    @commands.command()
    async def stop(self, ctx):
        """Stops the clan battle"""
        clan = find_clan(ctx.message)
        clan.drive_update()
        clan.conn.close()
        del clans[clans.index(clan)]
        await ctx.message.add_reaction(e.ok)

    @commands.command()
    async def shutdown(self, ctx):
        """Stops the bot"""
        for clan in clans:
            clan.drive_update()
            clan.conn.close()
        await ctx.message.add_reaction(e.ok)
        await bot.close()

    @commands.command()
    async def reload(self, ctx):
        await ctx.message.add_reaction(e.ok)
        for c_mem in ctx.guild.get_role(cfg.CLAN_ROLE_ID).members:
            found = False
            for db_mem in db.clan.members:
                if c_mem.id == db_mem.discord_id:
                    print('found')
                    found = True
                    break
            if not found:
                data = (c_mem.id, c_mem.display_name, 3, 0, 0, 0, 0, 0, 0)
                db.insert('members_data', data)
                db.clan.members.append(db.Member(data=data))
        await ctx.send(f'Members list has been reloaded {ctx.author.mention}', delete_after=5)


bot.add_cog(Global_commands(bot))
bot.add_cog(Cb_commands(bot))
bot.add_cog(Mod_commands(bot))


async def cb_init(channel, db_name, clan_config):
    msg = None
    if db_name:
        if cfg.ENV > 0:
            db_name += '_dev'
        jobstores = {'default': SQLAlchemyJobStore(url='sqlite:///{}.db'.format(db_name))}
        job_defaults = {'coalesce': True, 'misfire_grace_time': None}
        scheduler = AsyncIOScheduler()
        scheduler.configure(jobstores=jobstores, job_defaults=job_defaults, timezone=pytz.timezone('Japan'))
        path = f'{db_name}.db'
        if os.path.isfile(path) or (not cfg.DISABLE_DRIVE and db.download_db(path)):
            msg = f'{db_name} has been loaded.'
            clan = db.Clan(db_name, clan_config)
            clans.append(clan)
        else:
            db.create_cb_db(db_name, channel.guild.id, channel.id)
            clan = db.Clan(db_name, clan_config)
            clans.append(clan)
            for member in channel.guild.get_role(clan_config['CLAN_ROLE_ID']).members:
                clan.add_member(member)
            scheduler.add_job(daily_reset, 'interval', args=[db_name], days=1, start_date=datetime.datetime(2021, 1, 10, 5, 0, 0))
            msg = '{} has been created.'.format(db_name)
            clan.drive_update()

        mods_members = channel.guild.get_role(clan_config['CLAN_MOD_ROLE_ID']).members
        for member in mods_members:
            if clan.find_member(member.id):
                clan.mods.append(member.id)
        clan.is_daily_reset = False
        scheduler.start()
        print(msg)
        scheduler.print_jobs()
        await channel.send(msg, delete_after=5)
        clan.ui = Ui()
        await clan.ui.start(channel, clan)


def daily_reset(name):
    for clan in clans:
        clan.is_daily_reset = True


# def bot_export(message):
#     file = False
#     file2 = False
#     if (message.author.id in cfg.MODS):
#         m_split = message.content.split()
#         if len(m_split) > 1:
#             if os.path.isfile(m_split[1] + '.db'):
#                 file = db.data_csv(m_split[1])
#                 file2 = db.chat_log_csv(m_split[1])
#                 msg = f'{file} and {file2} have been sent to your DM! {message.author.mention}'
#             else:
#                 msg = f"{m_split[1]}.db doesn't exist"
#         else:
#             msg = f'Argument not found.\nUse "{P}export <cb_file_name>" to export your clan battle file. (mod only)'
#     else:
#         msg = f'You dont have permission to use this command {message.author.mention}'
#     return (msg, file, file2)


try:
    bot.run(cfg.TOKEN)
except RuntimeError:
    pass
print('Client closed')
while 1:
    time.sleep(500)
