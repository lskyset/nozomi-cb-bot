import time

import discord

from nozomi_cb_bot.cb import Boss
from nozomi_cb_bot.config import TIER_COLOURS, jst_time


class BossEmbed(discord.Embed):
    def __init__(self, boss: Boss):
        self._boss = boss
        super().__init__(title=self._boss_title())
        self.set_author(name=f"Wave {self._boss.wave} (T{self._boss.tier})")
        self.description = self._boss_description()
        self.set_image(url=boss.img_url)
        self._set_boss_footer()
        self.colour = discord.Colour.from_rgb(*TIER_COLOURS[self._boss.tier - 1])

    def _boss_title(self) -> str:
        title = f"Boss {self._boss.number} : {self._boss.name}"
        if self._boss.wave_offset > 0:
            title += f" [+{self._boss.wave_offset}]"
        return title

    def _boss_description(self):
        # title
        hp_text = "HP : *{:,} / {:,}*\n".format(self._boss.hp, self._boss.max_hp)

        # previous damage log
        p_damage_log = self._boss.get_damage_log(wave_offset=-1)
        p_damage_text = ""
        if p_damage_log:
            p_damage_text += "**Previous wave :** \n"
            for hit in p_damage_log:
                p_damage_text += f"-**{hit['member_name']}** dealt *{int(hit['damage']):,}* damages. {'(OF)' * hit['overflow']} \n"

        # damage log
        damage_log = self._boss.get_damage_log()
        damage_text = ""
        if damage_log:
            damage_text += "**Damage logs :** \n"
            for hit in damage_log:
                damage_text += f"-**{hit['member_name']}** dealt *{int(hit['damage']):,}* damages. {'(OF)' * hit['overflow']} \n"

        # queue
        queue = self._boss.get_queue()
        waiting_queue = self._boss.get_waiting()
        queue_text = ""
        if queue or waiting_queue:
            queue_text += "**Queue :** \n"
            if queue:
                for member_data in queue:
                    member = self._boss.clan.find_member(member_data["member_id"])
                    time_text = ""
                    note_text = f": {member_data['note']}" * bool(member_data["note"])
                    if (
                        self._boss.queue_timeout
                        and self._boss.hitting_member_id == 0
                        and member.discord_id == self._boss.get_first_in_queue_id()
                        and self._boss.clan.timeout_minutes > 0
                    ):
                        time_text += time.strftime(
                            "[%M:%S] ",
                            time.gmtime(
                                max(
                                    (
                                        self._boss.queue_timeout - jst_time()
                                    ).total_seconds(),
                                    0,
                                )
                            ),
                        )
                    if self._boss.clan.timeout_minutes == 0:
                        time_text += f'[<t:{member_data["timestamp"]}:R>]'

                    queue_text += f"-{time_text} {member.name} {note_text} {' (OF)' * member.of_status}\n"
            if waiting_queue:
                for member_data in waiting_queue:
                    member = self._boss.clan.find_member(member_data["member_id"])
                    note_text = f": {member_data['note']}" * bool(member_data["note"])
                    queue_text += f"-[Wave{member_data['wave']}] {member.name}{note_text}{' (OF)' * member.of_status}\n"
        text_list = [
            text
            for text in (hp_text, p_damage_text, damage_text, queue_text)
            if len(text)
        ]
        return "\n".join(text_list).rstrip()

    def _set_boss_footer(self) -> None:
        if self._boss.hitting_member is None:
            self.remove_footer()
            return

        footer_text = "{0.discord_member.display_name} is curently hitting {0.remaining_hits}/3".format(
            self._boss.hitting_member
        )
        if self._boss.hitting_member.of_status:
            footer_text += " (OF)"

        if self._boss.syncing_member:
            footer_text += (
                f" with {self._boss.syncing_member.discord_member.display_name}"
            )
            if self._boss.syncing_member.of_status:
                footer_text += " (OF)"
        avatar_url = None
        if self._boss.hitting_member.discord_member.avatar is not None:
            avatar_url = self._boss.hitting_member.discord_member.avatar.url
        self.set_footer(
            text=footer_text,
            icon_url=avatar_url,
        )
