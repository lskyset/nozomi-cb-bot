import asyncio
import datetime
import time
from dataclasses import dataclass, field

import discord

from nozomi_cb_bot import config as cfg
from nozomi_cb_bot.cb.boss import Boss
from nozomi_cb_bot.cb.clan import Clan


@dataclass
class BossBox:
    message: discord.MessageType
    boss: Boss
    clan: Clan
    embed: discord.Embed = field(default_factory=discord.Embed)
    wave_offset: int = 0
    discord_hm: discord.Member = None
    discord_sm: discord.Member = None
    hit_button: discord.Button = discord.Button(
        label="Hit",
        custom_id="hit",
        style=discord.ButtonColor.grey,
        emoji="⚔️",
    )
    disabled_hit_button: discord.Button = discord.Button(
        label="Hit",
        custom_id="hit",
        style=discord.ButtonColor.grey,
        emoji="⚔️",
        disabled="true",
    )
    queue_button: discord.Button = discord.Button(
        label="Queue",
        custom_id="queue",
        style=discord.ButtonColor.grey,
        emoji="🕒",
    )
    overview_button: discord.Button = None

    def __post_init__(self):
        self.embed.set_image(url=self.boss.img)

    async def update(self) -> None:

        self.wave_offset = self.boss.wave - self.clan.wave
        if self.wave_offset > 1:
            self.boss.queue_timeout = None
        elif self.boss.queue_timeout is None and not self.boss.hitting_member_id:
            self.boss.queue_timeout = cfg.jst_time(minutes=self.clan.timeout_minutes)
        self.embed.set_author(name=f"Wave {self.boss.wave} (T{self.boss.tier})")
        self.embed.title = f"Boss {self.boss.number} : {self.boss.name}{f' [+{self.wave_offset}]' * (self.wave_offset > 0)}"
        self.set_description()
        await self.set_footer()
        self.set_components()

        await self.message.edit(
            content=None, embed=self.embed, components=self.components
        )

    def set_description(self) -> None:
        # title
        hp_text = "HP : *{:,} / {:,}* \n\n".format(
            self.boss.hp, self.boss.max_hp[self.boss.tier - 1]
        )

        # previous damage log
        p_damage_log = self.boss.get_damage_log(wave_offset=-1)
        p_damage_text = ""
        if p_damage_log:
            p_damage_text += "**Previous wave :** \n"
            for hit in p_damage_log:
                p_damage_text += f"-**{hit['member_name']}** dealt *{int(hit['damage']):,}* damages. {'(OF)' * hit['overflow']} \n"
            p_damage_text += "\n"

        # damage log
        damage_log = self.boss.get_damage_log()
        damage_text = ""
        if damage_log:
            damage_text += "**Damage logs :** \n"
            for hit in damage_log:
                damage_text += f"-**{hit['member_name']}** dealt *{int(hit['damage']):,}* damages. {'(OF)' * hit['overflow']} \n"
            damage_text += "\n"

        # queue
        queue = self.boss.get_queue()
        waiting_queue = self.boss.get_waiting()
        queue_text = ""
        if queue or waiting_queue:
            queue_text += "**Queue :** \n"
            if queue:
                for member_data in queue:
                    member = self.clan.find_member(member_data["member_id"])
                    time_text = ""
                    note_text = f": {member_data['note']}" * bool(member_data["note"])
                    if (
                        self.boss.queue_timeout
                        and self.boss.hitting_member_id == 0
                        and member.discord_id == self.boss.get_first_in_queue_id()
                        and self.clan.timeout_minutes > 0
                    ):
                        time_text += time.strftime(
                            "[%M:%S] ",
                            time.gmtime(
                                max(
                                    (
                                        self.boss.queue_timeout - cfg.jst_time()
                                    ).total_seconds(),
                                    0,
                                )
                            ),
                        )
                    if self.clan.timeout_minutes == 0:
                        time_text += time.strftime(
                            "[%H:%M:%S]",
                            time.gmtime(
                                (
                                    datetime.datetime.now()
                                    - datetime.datetime.fromtimestamp(
                                        member_data["timestamp"]
                                    )
                                ).seconds
                            ),
                        )
                    queue_text += f"-{time_text} {member.name} {note_text} {' (OF)' * member.of_status}\n"
            if waiting_queue:
                for member_data in waiting_queue:
                    member = self.clan.find_member(member_data["member_id"])
                    note_text = f": {member_data['note']}" * bool(member_data["note"])
                    queue_text += f"-[Wave{member_data['wave']}] {member.name}{note_text}{' (OF)' * member.of_status}\n"
            queue_text += "\n"

        description_text = f"{hp_text}{p_damage_text}{damage_text}{queue_text}"
        self.embed.description = description_text

    async def set_footer(self) -> None:
        hm_id = self.boss.hitting_member_id
        sm_id = self.boss.syncing_member_id
        if hm_id:
            if not self.discord_hm or self.discord_hm.id != hm_id:
                self.discord_hm = await self.message.guild.fetch_member(hm_id)
            clan_hm = self.clan.find_member(hm_id)
            if sm_id:
                if not self.discord_sm or self.discord_sm.id != sm_id:
                    self.discord_sm = await self.message.guild.fetch_member(sm_id)
                self.embed.set_footer(
                    text=f'{self.discord_hm.display_name} is curently hitting {clan_hm.remaining_hits}/3{" (OF)" * clan_hm.of_status} with {self.discord_sm.display_name}',
                    icon_url=self.discord_hm.avatar_url,
                )
            else:
                self.embed.set_footer(
                    text=f'{self.discord_hm.display_name} is curently hitting {clan_hm.remaining_hits}/3{" (OF)" * clan_hm.of_status}',
                    icon_url=self.discord_hm.avatar_url,
                )
        else:
            self.embed.set_footer(text="")

    def set_components(self) -> None:
        if (
            self.boss.hitting_member_id
            or self.wave_offset > 1
            or self.boss.tier != self.clan.tier
        ):
            hit_button = self.disabled_hit_button
        else:
            hit_button = self.hit_button
        self.components = [
            discord.ActionRow(
                hit_button,
                self.queue_button,
                self.overview_button,
            )
        ]


@dataclass
class OverviewBox:
    message: discord.MessageType
    clan: Clan
    embed: discord.Embed = discord.Embed(title="Overview")
    b1_button: discord.Button = None
    b2_button: discord.Button = None
    b3_button: discord.Button = None
    b4_button: discord.Button = None
    b5_button: discord.Button = None
    log_button = discord.Button(
        label="Logs",
        custom_id="logs",
        style=discord.ButtonColor.grey,
        emoji="📝",
    )

    async def update(self) -> None:
        self.embed.set_author(name=f"Tier {self.clan.tier}: Wave {self.clan.wave}")
        self.embed.clear_fields()
        for boss in self.clan.bosses:
            wave_offset = boss.wave - self.clan.wave
            self.embed.add_field(
                name=f"Boss {boss.number} : {boss.name}",
                value=f"**Wave {boss.wave}**{f' (+{wave_offset})' * (wave_offset > 0)} \n"
                + f"**HP :** *{boss.hp  // 10 ** 6}M / {boss.max_hp[boss.tier - 1] // 10 ** 6}M*\n",
            )
        hits_left = 0
        for member in self.clan.members:
            hits_left += member.remaining_hits
        self.embed.add_field(
            name="Clan info",
            value=f"**Hits done :** {len(self.clan.members) * 3 - hits_left} / {len(self.clan.members) * 3}",
        )
        self.components = [
            discord.ActionRow(
                self.b1_button,
                self.b2_button,
                self.b3_button,
                self.b4_button,
                self.b5_button,
            )
        ]  # ,self.log_button]
        await self.message.edit(
            content=None, embed=self.embed, components=self.components
        )


@dataclass(init=False)
class Ui:
    clan: Clan
    channel: discord.ChannelType
    b1: BossBox
    b2: BossBox
    b3: BossBox
    b4: BossBox
    b5: BossBox
    overview: OverviewBox

    async def start(self, channel: discord.ChannelType, clan: Clan) -> None:
        self.clan = clan
        self.channel = channel

        for boss in self.clan.bosses:
            if boss.message_id:
                msg = self.channel.get_partial_message(boss.message_id)
                await msg.delete()
            msg = await self.channel.send(f"Loading B{boss.number}...")
            boss.message_id = msg.id
            boss.update()
            await asyncio.sleep(1)
            setattr(self, f"b{boss.number}", BossBox(msg, boss, clan))

        if clan.overview_message_id:
            msg = self.channel.get_partial_message(clan.overview_message_id)
            await msg.delete()
        msg = await self.channel.send("Loading overview...")
        self.overview = OverviewBox(msg, clan)
        clan.overview_message_id = msg.id
        clan.update()

        for boss in self.clan.bosses:
            getattr(self, f"b{boss.number}").overview_button = discord.Button(
                label="Overview",
                style=discord.ButtonColor.grey_url,
                url=self.overview.message.jump_url,
            )
            setattr(
                self.overview,
                f"b{boss.number}_button",
                discord.Button(
                    label=f"B{boss.number}",
                    style=discord.ButtonColor.grey_url,
                    url=getattr(self, f"b{boss.number}").message.jump_url,
                ),
            )
            await asyncio.sleep(0.5)
        await self.update()

    async def update(self, message_id: int = None) -> None:
        for boss in self.clan.bosses:
            if message_id is None or message_id == boss.message_id:
                await getattr(self, f"b{boss.number}").update()
                await asyncio.sleep(0.5)
        await self.overview.update()
