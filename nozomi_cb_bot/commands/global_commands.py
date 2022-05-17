from discord.ext import commands

from nozomi_cb_bot.nozomi import Nozomi


class GlobalCommands(commands.Cog, name="Global Commands"):  # type: ignore
    """Global Commands are commands that can be used at any time"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    async def hello(self, ctx: commands.Context):
        """Says hello and mention the user (used for testing purposes)"""
        msg = f"Hello {ctx.author.mention}"
        await ctx.send(msg)


async def setup(bot: Nozomi):
    await bot.add_cog(GlobalCommands(bot))
