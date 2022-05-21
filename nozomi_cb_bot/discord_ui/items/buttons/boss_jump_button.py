import discord

from nozomi_cb_bot.cb import Boss


class BossJumpButton(discord.ui.Button):
    def __init__(self, boss: Boss):
        url = None
        if boss.message is not None:
            url = boss.message.jump_url
        super().__init__(
            label=f"B{boss.number}",
            url=url,
        )
