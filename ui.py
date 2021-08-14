import discord
import asyncio
import time

import config as cfg


class Ui():
    def __init__(self):
        self.clan = None
        self.channel = None
        self.b1 = None
        self.b2 = None
        self.b3 = None
        self.b4 = None
        self.b5 = None
        self.overview = None

    async def start(self, channel, clan):
        self.clan = clan
        self.channel = channel

        for boss in clan.bosses:
            if boss.message_id:
                msg = self.channel.get_partial_message(boss.message_id)
                await msg.delete()
            msg = await self.channel.send(f'Loading B{boss.number}...')
            boss.message_id = msg.id
            boss.update()
            await asyncio.sleep(1)
            setattr(self, f'b{boss.number}', Boss_box(msg, boss, clan))

        if clan.overview_message_id:
            msg = self.channel.get_partial_message(clan.overview_message_id)
            await msg.delete()
        msg = await self.channel.send('Loading overview...')
        self.overview = Overview_box(msg, clan)
        clan.overview_message_id = msg.id
        clan.update()

        for boss in clan.bosses:
            getattr(self, f'b{boss.number}').overview_button = discord.Button(
                label='Overview',
                style=discord.ButtonColor.grey_url,
                url=self.overview.message.jump_url,
            )
            setattr(self.overview, f'b{boss.number}_button', discord.Button(
                label=f'B{boss.number}',
                style=discord.ButtonColor.grey_url,
                url=getattr(self, f'b{boss.number}').message.jump_url,
            ))
            await asyncio.sleep(.5)
        await self.update()

    async def update(self, message_id=None):
        for boss in self.clan.bosses:
            if message_id is None or message_id == boss.message_id:
                await getattr(self, f'b{boss.number}').update()
                await asyncio.sleep(.5)
        await self.overview.update()


class Boss_box():
    def __init__(self, message, boss, clan):
        self.message = message
        self.boss = boss
        self.clan = clan
        self.embed = discord.Embed()
        self.embed.set_image(url=self.boss.img)
        self.wave_offset = 0

        self.discord_hm = None
        self.discord_sm = None

        self.hit_button = discord.Button(
            label="Hit",
            custom_id='hit',
            style=discord.ButtonColor.grey,
            emoji="⚔️",
        )
        self.disabled_hit_button = discord.Button(
            label="Hit",
            custom_id='hit',
            style=discord.ButtonColor.grey,
            emoji="⚔️",
            disabled="true",
        )
        self.queue_button = discord.Button(
            label="Queue",
            custom_id='queue',
            style=discord.ButtonColor.grey,
            emoji="🕒",
        )
        self.overview_button = None

    async def update(self):
        self.wave_offset = self.boss.wave - self.clan.current_wave
        if self.wave_offset > 1:
            self.boss.queue_timeout = None
        elif self.boss.queue_timeout is None and not self.boss.hitting_member_id:
            self.boss.queue_timeout = cfg.jst_time(minutes=cfg.timeout_minutes)
        self.embed.set_author(name=f"Wave {self.boss.wave} (T{self.boss.tier})")
        self.embed.title = f"Boss {self.boss.number} : {self.boss.name}{f' [+{self.wave_offset}]' * (self.wave_offset > 0)}"
        self.set_description()
        await self.set_footer()
        self.set_components()
        await self.message.edit(content=None, embed=self.embed, components=self.components)

    def set_description(self):
        # title
        hp_text = "HP : *{:,} / {:,}* \n\n".format(self.boss.hp, self.boss.max_hp[self.boss.tier - 1] * 10 ** 6)

        # previous damage log
        p_damage_log = self.boss.get_damage_log(wave_offset=-1)
        p_damage_text = ''
        if p_damage_log:
            p_damage_text += '**Previous wave :** \n'
            for hit in p_damage_log:
                p_damage_text += f"-**{hit['member_name']}** dealt *{int(hit['damage']):,}* damages. {'(OF)' * hit['overflow']} \n"
            p_damage_text += '\n'

        # damage log
        damage_log = self.boss.get_damage_log()
        damage_text = ''
        if damage_log:
            damage_text += '**Damage logs :** \n'
            for hit in damage_log:
                damage_text += f"-**{hit['member_name']}** dealt *{int(hit['damage']):,}* damages. {'(OF)' * hit['overflow']} \n"
            damage_text += '\n'

        # queue
        queue = self.boss.get_queue()
        queue_text = ''
        if queue:
            queue_text += '**Queue :** \n'
            for member_data in queue:
                member = self.clan.find_member(member_data['member_id'])
                time_left = ''
                if self.boss.queue_timeout and self.boss.hitting_member_id == 0 and member.discord_id == self.boss.get_first_in_queue_id():
                    time_left += time.strftime(' [%M:%S]', time.gmtime(max((self.boss.queue_timeout - cfg.jst_time()).total_seconds(), 0)))
                queue_text += f"-{member.name}{' (OF)' * member.of_status}{time_left} \n"
            queue_text += '\n'

        description_text = f'{hp_text}{p_damage_text}{damage_text}{queue_text}'
        self.embed.description = description_text

    async def set_footer(self):
        hm_id = self.boss.hitting_member_id
        sm_id = self.boss.syncing_member_id
        if hm_id:
            if not self.discord_hm or self.discord_hm.id != hm_id:
                self.discord_hm = await self.message.guild.fetch_member(hm_id)
            clan_hm = self.clan.find_member(hm_id)
            if sm_id:
                if not self.discord_sm or self.discord_sm.id != sm_id:
                    self.discord_sm = await self.message.guild.fetch_member(sm_id)
                self.embed.set_footer(text=f'{self.discord_hm.display_name} is curently hitting {clan_hm.remaining_hits}/3{" (OF)" * clan_hm.of_status} with {self.discord_sm.display_name}', icon_url=self.discord_hm.avatar_url)
            else:
                self.embed.set_footer(text=f'{self.discord_hm.display_name} is curently hitting {clan_hm.remaining_hits}/3{" (OF)" * clan_hm.of_status}', icon_url=self.discord_hm.avatar_url)
        else:
            self.embed.set_footer(text='')

    def set_components(self):
        if self.boss.hitting_member_id or self.wave_offset > 1 or self.boss.tier != self.clan.current_tier:
            hit_button = self.disabled_hit_button
        else:
            hit_button = self.hit_button
        self.components = [discord.ActionRow(
            hit_button,
            self.queue_button,
            self.overview_button,
        )]


class Overview_box():
    def __init__(self, message, clan):
        self.message = message
        self.bosses = clan.bosses
        self.clan = clan
        self.embed = discord.Embed()
        self.embed.title = 'Overview'

        self.b1_button = None
        self.b2_button = None
        self.b3_button = None
        self.b4_button = None
        self.b5_button = None
        self.log_button = discord.Button(
            label="Logs",
            custom_id='logs',
            style=discord.ButtonColor.grey,
            emoji="📝",
        )

    async def update(self):
        self.embed.set_author(name=f"Tier {self.clan.current_tier}: Wave {self.clan.current_wave}")
        self.embed.clear_fields()
        for boss in self.bosses:
            wave_offset = boss.wave - self.clan.current_wave
            self.embed.add_field(
                name=f'Boss {boss.number} : {boss.name}',
                value=f"**Wave {boss.wave}**{f' (+{wave_offset})' * (wave_offset > 0)} \n" + f"**HP :** *{boss.hp  // 10 ** 6}M / {boss.max_hp[boss.tier - 1]}M*\n",
            )
        hits_left = 0
        for member in self.clan.members:
            hits_left += member.remaining_hits
        self.embed.add_field(
            name='Clan info',
            value=f'**Hits done :** {len(self.clan.members) * 3 - hits_left} / {len(self.clan.members) * 3}',
        )
        self.components = [discord.ActionRow(
            self.b1_button,
            self.b2_button,
            self.b3_button,
            self.b4_button,
            self.b5_button,
        )]  # ,self.log_button]
        await self.message.edit(content=None, embed=self.embed, components=self.components)

#  ############## OLD CODE ####################

# class Box():
#     def __init__(self, message):

#         self.scheduler = AsyncIOScheduler()
#         self.scheduler.configure(job_defaults={'coalesce': True, 'misfire_grace_time': None}, timezone=pytz.timezone('Japan'))
#         self.scheduler.start()

#         self.embed_ = discord.Embed()
#         self.embed_.set_image(url=db.clan.current_boss.img)
#         self.embed_.set_author(name="Wave {0.current_wave} (T{0.current_tier})".format(db.clan))
#         self.embed_.title = "Boss {0.current_boss_num} : {0.current_boss.name}".format(db.clan)
#         self.boss_max_hp = db.clan.current_boss.max_hp[db.clan.current_tier - 1] * 1000000
#         self.msg = message

#         self.damage_list = ''
#         self.message_board = ''
#         self.queue_list = []
#         self.claim_timer_str = ''
#         self.queue_timeout_str = ''
#         self.embed_.description = self.description()
#         self.react_list = [e.hit, e.queue]
#         self.role_restrict = True
#         self.queue_timer = None
#         self.hitting_user = None
#         self.sync_user = None

#     async def create(self):
#         self.msg = await self.msg.channel.send(embed=self.embed_)
#         boxdict[(self.msg.channel.id, self.msg.id)] = self
#         boss_role = self.msg.channel.guild.get_role(cfg.ROLE_IDS[db.clan.current_boss_num - 1])
#         self.priority_list = []
#         if db.clan.current_tier >= 3 and not db.clan.rush_hour:
#             self.priority_list = boss_role.members
#         if self.priority_list:
#             await self.claim_timer(cfg.jst_time(minutes=5))
#         else:
#             self.role_restrict = False
#             await self.update()

#     def description(self):
#         queue_str = ''
#         damage_str = ''
#         message_str = ''
#         boss_status = "**HP :** *{:,}/{:,}* \n".format(db.clan.current_boss.hp, db.clan.current_boss.max_hp[db.clan.current_tier - 1] * 1000000)
#         if self.damage_list:
#             damage_str = f'\n**Damage logs :**{self.damage_list} \n'
#         if self.message_board:
#             message_str = f'\n**Message board :**{self.message_board} \n'
#         if self.queue_list:
#             queue_str = '\n**Queue :** \n'
#             for user in self.queue_list:
#                 of = ' (OF)' * db.clan.find_member(user.id).of_status
#                 timer = ''
#                 if self.queue_timeout_str and user == self.queue_list[0]:
#                     seconds_left = (self.queue_timer - cfg.jst_time()).total_seconds()
#                     if seconds_left > 0:
#                         self.queue_timeout_str = time.strftime(' [%M:%S]', time.gmtime(seconds_left))
#                         timer = self.queue_timeout_str
#                 queue_str += '-{0.display_name}{1}{2} \n'.format(user, of, timer)
#         description = f"{boss_status}{damage_str}{queue_str}{self.claim_timer_str}{message_str}"
#         if description.endswith('\n'):
#             description = description[:-2]
#         return description

#     async def update(self, create=False):
#         self.loading = True
#         self.embed_.description = self.description()
#         if (not create):
#             await self.msg.edit(embed=self.embed_)
#         for react in self.react_list:
#             await self.msg.add_reaction(react)
#         await asyncio.sleep(1)
#         self.loading = False

#     async def queue(self, user, overflow=False):
#         msg = ''
#         if self.role_restrict is True and user not in self.priority_list:
#             msg = f"You don't have priority to queue for this boss {user.mention}"
#         else:
#             clan_member = db.clan.find_member(user.id)
#             if not clan_member.remaining_hits > 0 and not clan_member.of_status:
#                 msg = f"You don't have any hits left {user.mention}\nYour were added in the queue with OF"
#                 overflow = True
#             if overflow:
#                 clan_member.of_status = True
#             if len(self.queue_list) < 10:
#                 if user == self.hitting_user:
#                     msg = f"You can't queue while you are hitting {user.mention}"
#                 elif user in self.queue_list:
#                     msg = f"You are already in the queue {user.mention}"
#                 else:
#                     self.queue_list.append(user)
#                     if self.queue_timer is None:
#                         await self.queue_timeout()
#                     if len(self.queue_list) == 10:
#                         self.react_list.pop(self.react_list.index(e.queue))
#                     await self.update()
#             else:
#                 msg = f'The queue is full {user.mention}'
#         if msg:
#             await self.msg.channel.send(msg, delete_after=5)

#     async def dequeue(self, user):
#         if user in self.queue_list:
#             index = self.queue_list.index(user)
#             self.queue_list.pop(index)
#             if index == 0:
#                 self.queue_timer = None
#                 self.queue_timeout_str = ''
#                 await self.queue_timeout(notif=True)
#             await self.update()
#         else:
#             await self.msg.channel.send(f'You are not in the queue {user.mention}', delete_after=5)

#     async def hitting(self, user, overflow=False, sync=None):
#         msg = ''
#         clan_member = db.clan.find_member(user.id)
#         if self.hitting_user:
#             if self.hitting_user == user:
#                 if sync:
#                     self.sync_user = sync
#                     footer_text = self.embed_.footer.text + ' with ' + sync.display_name
#                     self.embed_.set_footer(text=footer_text, icon_url=user.avatar_url)
#                     if self.sync_user in self.queue_list:
#                         index = self.queue_list.index(self.sync_user)
#                         self.queue_list.pop(index)
#                     await self.update()
#                 else:
#                     msg = "You are already hitting {0.mention}".format(user)
#             else:
#                 msg = f"{self.hitting_user.display_name} is already hitting {user.mention}"
#         elif self.sync_user:
#             msg = f"{self.sync_user.display_name} is already hitting {user.mention}"
#         else:
#             check1 = self.queue_list and user != self.queue_list[0]
#             check2 = self.role_restrict and user not in self.priority_list
#             if check1 or check2:
#                 msg = "You don't have priority to hit this boss {0.mention}".format(user)
#             else:
#                 footer_text = '{0.display_name} is currently hitting {1.remaining_hits}/3'
#                 if clan_member.remaining_hits <= 0 and not clan_member.of_status:
#                     msg = "You don't have any hits left {0.mention}\nYour hit was counted as OF".format(user)
#                     overflow = True
#                 if overflow or clan_member.of_status:
#                     clan_member.of_status = True
#                     footer_text += ' (OF)'
#                 if sync:
#                     self.sync_user = sync
#                     footer_text += f' with {sync.display_name}'
#                     if self.sync_user in self.queue_list:
#                         index = self.queue_list.index(self.sync_user)
#                         self.queue_list.pop(index)
#                 if self.queue_list and user == self.queue_list[0]:
#                     self.queue_list.pop(0)
#                     if len(self.queue_list) == 2:
#                         self.react_list.append(e.queue)
#                 self.hitting_user = user
#                 self.embed_.set_footer(text=footer_text.format(user, db.clan.find_member(user.id)), icon_url=user.avatar_url)
#                 self.react_list.pop(self.react_list.index(e.hit))
#                 await self.msg.clear_reaction(e.hit)
#                 await self.update()
#         if msg:
#             await self.msg.channel.send(msg, delete_after=5)

#     async def cancel_hit(self, user, d=False):
#         if user == self.hitting_user:
#             self.hitting_user = None
#             if not d:
#                 self.sync_user = None
#         elif user == self.sync_user:
#             self.sync_user = None
#         else:
#             await self.msg.channel.send('You are not hitting {user.mention}', delete_after=5)
#             return
#         if not (self.hitting_user or self.sync_user):
#             await self.msg.clear_reactions()
#             self.react_list.insert(0, e.hit)
#             self.embed_.set_footer()
#         else:
#             footer_text = '{0.display_name} is curently hitting {1.remaining_hits}/3'
#             if self.hitting_user:
#                 footer_user = self.hitting_user
#             else:
#                 footer_user = self.sync_user
#             self.embed_.set_footer(text=footer_text.format(footer_user, db.clan.find_member(footer_user.id)), icon_url=footer_user.avatar_url)
#         await self.update()

#     async def claim_timer(self, end_time):
#         self.seconds_left = (end_time - cfg.jst_time()).total_seconds()
#         if self.seconds_left > 0:
#             next_time = cfg.jst_time(seconds=min(30, self.seconds_left))
#             self.scheduler.add_job(self.claim_timer, 'date', args=[end_time], run_date=next_time)
#             self.claim_timer_str = '\n{} {} left for reserved hits \n'.format(e.queue, time.strftime('%M min %S sec', time.gmtime(self.seconds_left)))
#             await self.update()
#         else:
#             self.claim_timer_str = ''
#             await self.update()
#             self.role_restrict = False

#     async def queue_timeout(self, notif=False):
#         if self.hitting_user or self.sync_user:
#             self.queue_timer = None
#             self.queue_timeout_str = ''
#         elif self.queue_timer:
#             seconds_left = (self.queue_timer - cfg.jst_time()).total_seconds()
#             if seconds_left > 0:
#                 next_time = cfg.jst_time(seconds=min(30, seconds_left))
#                 self.scheduler.add_job(self.queue_timeout, 'date', run_date=next_time)
#                 self.queue_timeout_str = time.strftime(' [%M:%S]', time.gmtime(seconds_left))
#                 if not self.role_restrict:
#                     await self.update()
#             else:
#                 await self.dequeue(self.queue_list[0])
#                 self.queue_timer = None
#                 self.queue_timeout_str = ''
#         elif self.queue_list:
#             self.queue_timer = cfg.jst_time(minutes=15)
#             seconds_left = (self.queue_timer - cfg.jst_time()).total_seconds()
#             self.scheduler.add_job(self.queue_timeout, 'date', run_date=cfg.jst_time(seconds=30))
#             self.queue_timeout_str = time.strftime(' [%M:%S]', time.gmtime(seconds_left))
#             await self.msg.channel.send('You have 15 minutes to claim your hit {0.mention}'.format(self.queue_list[0]), delete_after=(5 + 25 * notif))

#     async def close(self):
#         self.scheduler.shutdown()
#         await self.msg.clear_reactions()
#         self.embed_.set_footer()
#         boss_status = "**HP :** *{:,}/{:,}*\n".format(0, self.boss_max_hp)
#         damage_str = ''
#         message_str = ''
#         if self.damage_list:
#             damage_str = f'\n**Damage logs :**{self.damage_list} \n'
#         if self.message_board:
#             message_str = f'\n**Message board :**{self.message_board} \n'
#         self.embed_.description = f'{boss_status}{damage_str}{message_str}\n*Boss has been defeated.*'
#         await self.msg.edit(embed=self.embed_)
#         del self