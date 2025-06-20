"""Bot handlers for the Telegram bot."""

# Standard library imports
import datetime
from typing import List

# Third-party imports
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    # BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    Message,
)

# Local application imports
from bot.filters import IsAdmin, IsPremium
from bot.middlewares import LongOperation
from config import get_config, get_logger
from db.repository import ChatRepository, UserRepository
from db.schemas import Chat as ChatSchema
from db.schemas import UserCreate
from db.session import get_session
from utils.i18n import t

LOG_LEVEL = get_config().LOG_LEVEL
LOG = get_logger(__name__, log_level=LOG_LEVEL)

# Temporary placeholder for BOT_ADMIN_ID and t
BOT_ADMIN_ID = get_config().BOT_ADMIN_ID


# Create routers
root_router = Router()
admin_router = Router()
premium_router = Router()

# Apply middleware to root router
root_router.message.middleware(LongOperation())

# Apply filters
admin_router.message.filter(IsAdmin())
premium_router.message.filter(IsPremium())


# =============================
# Command Handlers
# =============================
@root_router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """Handle /start command."""
    if not message.from_user:
        return

    locale = message.from_user.language_code or "en"
    is_bot = message.from_user.is_bot
    is_admin = message.from_user.id == BOT_ADMIN_ID
    is_premium = message.from_user.is_premium or False

    session = get_session()
    try:
        # Create chat record at the beginning
        chat_repo = ChatRepository(session)
        chat_data = ChatSchema(
            id=message.chat.id,
            type=message.chat.type,
            title=getattr(message.chat, "title", None),
            username=getattr(message.chat, "username", None),
            first_name=getattr(message.chat, "first_name", None),
            last_name=getattr(message.chat, "last_name", None),
            is_forum=getattr(message.chat, "is_forum", False) or False,
            created_at=getattr(message.chat, "created_at", None) or datetime.datetime.now(),
        )
        chat_repo.try_create_chat(chat_data)

        user_repo = UserRepository(session)
        user_repo.save_user(
            UserCreate(
                chat_id=message.from_user.id,
                username=message.from_user.username or "",
                is_bot=is_bot,
                is_premium=is_premium,
            )
        )

        LOG.debug("User %d started the bot", message.from_user.id)
    except Exception as error:
        LOG.exception("Failed to save user on /start: %s", error)
    finally:
        session.close()

    msg = t(locale, "start.instructions")

    await message.answer(
        msg,
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )

    # Update commands based on user type
    await update_user_commands(message, is_admin, is_premium)


@root_router.message(Command("help"))
async def command_help_handler(message: Message) -> None:
    """Handle /help command."""
    if not message.from_user:
        return

    locale = message.from_user.language_code or "en"
    is_admin = message.from_user.id == BOT_ADMIN_ID
    is_premium = message.from_user.is_premium or False

    help_text = t(locale, "help.header") + "\n\n"
    help_text += t(
        locale,
        "help.general",
        cmdStart=t(locale, "cmd.start"),
        cmdHelp=t(locale, "cmd.help"),
        cmdQueue=t(locale, "cmd.queue"),
        cmdProfile=t(locale, "cmd.profile"),
        cmdBugs=t(locale, "cmd.bugs"),
    )

    # Show premium commands only for premium users
    if is_premium:
        help_text += "\n" + t(
            locale,
            "help.premium",
            cmdMonitor=t(locale, "cmd.monitor"),
            cmdUnmonitor=t(locale, "cmd.unmonitor"),
        )

    if is_admin:
        help_text += "\n" + t(
            locale,
            "help.admin",
            cmdUsers=t(locale, "cmd.users"),
            cmdHistory=t(locale, "cmd.history"),
            cmdBlock=t(locale, "cmd.block"),
            cmdUnblock=t(locale, "cmd.unblock"),
            cmdBlocklist=t(locale, "cmd.blocklist"),
            cmdRestart=t(locale, "cmd.restart"),
            cmdStatus=t(locale, "cmd.status"),
            cmdListbugs=t(locale, "cmd.listbugs"),
        )

    await message.answer(help_text, parse_mode="Markdown")


# =============================
# All other handlers: Not implemented
# =============================


@root_router.message()
async def not_implemented_handler(message: Message) -> None:
    await message.answer("User Not implemented!!!")


@premium_router.message()
async def not_implemented_premium_handler(message: Message) -> None:
    await message.answer("Premium Not implemented!!!")


@admin_router.message()
async def not_implemented_admin_handler(message: Message) -> None:
    await message.answer("Admin Not implemented!!!")


# =============================
# Helper Functions
# =============================
async def update_user_commands(message: Message, is_admin: bool, is_premium: bool) -> None:
    """Update user commands based on their status."""
    if not message.from_user or not message.bot:
        return

    LOG.debug(
        "Updating commands for user %d, is_admin: %s, is_premium: %s",
        message.from_user.id,
        is_admin,
        is_premium,
    )

    locale = message.from_user.language_code or "en"

    # Base commands
    commands: List[BotCommand] = [
        BotCommand(command="start", description=t(locale, "cmd.start")),
        BotCommand(command="help", description=t(locale, "cmd.help")),
        BotCommand(command="queue", description=t(locale, "cmd.queue")),
        BotCommand(command="profile", description=t(locale, "cmd.profile")),
        BotCommand(command="bugs", description=t(locale, "cmd.bugs")),
    ]

    # Premium commands - only for premium users
    if is_premium:
        LOG.debug("Adding premium commands")
        commands += [
            BotCommand(command="monitor", description=t(locale, "cmd.monitor")),
            BotCommand(command="unmonitor", description=t(locale, "cmd.unmonitor")),
        ]

    # Admin commands
    if is_admin:
        LOG.debug("Adding admin commands")
        commands += [
            BotCommand(command="users", description=t(locale, "cmd.users")),
            BotCommand(command="history", description=t(locale, "cmd.history")),
            BotCommand(command="block", description=t(locale, "cmd.block")),
            BotCommand(command="unblock", description=t(locale, "cmd.unblock")),
            BotCommand(command="blocklist", description=t(locale, "cmd.blocklist")),
            BotCommand(command="status", description=t(locale, "cmd.status")),
            BotCommand(command="restart", description=t(locale, "cmd.restart")),
            BotCommand(command="bugreport", description=t(locale, "cmd.listbugs")),
            BotCommand(command="bugs", description=t(locale, "cmd.bugs")),
            BotCommand(command="reset_auth", description="Reset Telegram auth code"),
            BotCommand(command="flush", description=t(locale, "cmd.flush")),
            BotCommand(command="welcome", description=t(locale, "cmd.welcome")),
        ]

    LOG.debug("Updating commands for user %d", message.from_user.id)

    result = await message.bot.set_my_commands(
        commands,
        scope=BotCommandScopeChat(chat_id=message.chat.id),
    )

    if result:
        LOG.debug("Commands updated for user %d", message.from_user.id)
    else:
        LOG.error("Failed to update commands for user %d", message.from_user.id)


def get_routers() -> List[Router]:
    """Get all bot routers."""
    return [root_router, admin_router, premium_router]
