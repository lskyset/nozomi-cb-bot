from enum import Enum

from discord.ext import commands


class ErrorMessage(Enum):
    NOT_MOD = "You don't have the permission to use this command."
    NO_ARGS = "Argument not found."
    NO_BOSS = "Boss not found."
    NO_DAMAGE = "Damages not found."
    NO_MENTION = "No mention Found."
    NO_SYNC_FOUND = "Sync user not found in the clan."
    BOSS_WAVE_AHEAD = (
        "You can't hit B{0.boss.number} because it's wave or tier is too far ahead."
    )
    MEMBER_ALREADY_HITTING = (
        "You are already hitting B{0.clan_member.hitting_boss_number}."
    )
    BOSS_ALREADY_HIT = "Someone is already hitting B{0.boss.number}."
    NO_PRIO = "You don't have priority to hit this boss."
    NOT_CLAIMED = "You must claim a hit before registering damages."
    QUEUE_ALREADY_HITTING = "You can't queue a boss you are already hitting."
    ALREADY_QUEUED = "You are already in the queue."
    SELF_SYNC = "You can't sync with yourself."
    SYNC_ALREADY_HITTING = (
        "{0.sync_member.name} is already hitting B{0.sync_member.hitting_boss_number}."
    )
    CANCEL = "You are not hitting any boss."
    IMP = "Wrong !imp format."


class ResponseMessage(Enum):
    HIT = "You are now hitting B{0.boss.number}."
    CANCEL = "You are no longer hitting B{0.boss.number}."
    DONE = "Your damage has been registered."


class HelpMessage(Enum):
    QUEUE = "Use for example `{0.bot.command_prefix}q b1` to queue for b1"
    DEQUEUE = "Use for example `{0.bot.command_prefix}dq b1` to unqueue yourself from b1's queue."
    HIT = "Use for example `{0.bot.command_prefix}h b1` to hit b1."
    SYNC = "Use for example `{0.bot.command_prefix}s b1 @Nozomi` to hit b1 with Nozomi"
    SYNC_MENTION = "You need to mention the person syncing with you."
    DONE = "Use `{0.bot.command_prefix}done <damage dealt>` to register your hit.\nNumbers ending with K and M are also supported"
    CLAIM = "For example use `{0.bot.command_prefix}h b1` to claim a hit on b1."
    EMPTY = ""


class NoticeMessage(Enum):
    NO_HITS_LEFT = "You don't have any hits left so your hit was counted as Overflow."
    SYNC = "Currently syncing with {0.syncing_member.discord_member.display_name}."
    EMPTY = ""


def get_success_message(ctx: commands.Context, response: ResponseMessage) -> str:
    return response.value.format(ctx)


def get_error_message(ctx: commands.Context, error: ErrorMessage) -> str:
    return error.value.format(ctx)


def get_help_message(ctx: commands.Context, help_message: HelpMessage) -> str:
    return help_message.value.format(ctx)


def get_notice_message(ctx: commands.context, notice: NoticeMessage) -> str:
    return notice.value.format(ctx)


async def bot_respond(ctx: commands.Context, content: str | None = None) -> None:
    if ctx.message.interaction is not None:
        if ctx.edit_original_message:
            return await ctx.message.interaction.edit_original_message(
                content=content, view=ctx.new_view
            )
        else:
            kwargs = {"content": content, "ephemeral": True}
            if ctx.new_view:
                kwargs["view"] = ctx.new_view
            return await ctx.message.interaction.followup.send(**kwargs)
    else:
        return await ctx.reply(content=content, delete_after=7)


async def command_error_respond(
    ctx: commands.Context,
    error: ErrorMessage,
    help_message: HelpMessage = HelpMessage.EMPTY,
) -> None:
    content = f"{get_error_message(ctx, error)}\n{get_help_message(ctx, help_message)}"
    await bot_respond(ctx, content=content)


async def command_success_respond(
    ctx: commands.Context,
    response_message: ResponseMessage,
    notice: NoticeMessage = NoticeMessage.EMPTY,
) -> None:
    content = f"{get_success_message(ctx, response_message)}\n{get_notice_message(ctx, notice)}"
    await bot_respond(ctx, content=content)
