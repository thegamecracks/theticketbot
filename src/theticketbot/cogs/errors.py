import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, Type, TypeVar, cast

import discord
from discord import app_commands
from discord.app_commands import locale_str as _
from discord.ext import commands

from theticketbot.bot import Bot, Context
from theticketbot.errors import AppCommandResponse
from theticketbot.translator import translate

log = logging.getLogger(__name__)

T = TypeVar("T")


async def append_error_code(ctx: object, content: str, error_code: str) -> str:
    trailer = _(
        # Message appended to some error responses caused by issues in the bot
        # {0}: the error code to be reported
        # {1}: the maintainer's mention
        "Error code: {0}\n"
        "If assistance is needed, please contact {1}."
    )
    trailer = await maybe_translate(ctx, trailer)
    trailer = trailer.format(error_code, get_owner_mention(ctx))
    return f"{content}\n{trailer}"


def get_owner_mention(ctx: object) -> str:
    if isinstance(ctx, discord.Interaction):
        ctx = cast(discord.Interaction[Bot], ctx)
        bot = ctx.client
    elif isinstance(ctx, commands.Context):
        ctx = cast(commands.Context[Bot], ctx)
        bot = ctx.bot
    else:
        # FIXME: should ctx really be generic?
        raise TypeError(f"Unsupported context type {type(ctx).__name__}")

    if bot.application is None:
        raise RuntimeError("Owner mention not available, bot must be logged in")

    return bot.application.owner.mention


def generate_error_code():
    return "".join(random.choices("0123456789ABCDEF", k=4))


async def maybe_translate(ctx: object, message: str | app_commands.locale_str) -> str:
    if isinstance(message, str):
        return message
    elif isinstance(ctx, discord.Interaction):
        return await translate(message, ctx)
    elif isinstance(ctx, commands.Context) and ctx.guild is not None:
        locale = ctx.guild.preferred_locale
        return await translate(message, ctx.bot, locale=locale)
    else:
        return message.message


@dataclass
class ErrorResponse:
    exc_types: Type[Exception] | tuple[Type[Exception], ...]
    content: str | app_commands.locale_str | None
    show_traceback: bool

    async def format(self, ctx: Any, error: Exception) -> str | None:
        if self.content is not None:
            content = await maybe_translate(ctx, self.content)
            return content.format(error)


class AppCommandErrorResponse(ErrorResponse):
    """A dedicated error formatter for :exc:`AppCommandResponse`."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            AppCommandResponse,
            None,
            *args,
            **kwargs,
        )

    async def format(self, ctx: discord.Interaction, error: Exception) -> str | None:
        assert isinstance(error, AppCommandResponse)
        message = error.message
        if isinstance(message, app_commands.locale_str):
            message = await translate(message, ctx, error.data)
        return message


class ErrorHandler(ABC, Generic[T]):
    responses: ClassVar[list[ErrorResponse]]

    @abstractmethod
    def get_command_name(self, ctx: T, /) -> str | None:
        """Returns the name of the command that was invoked, if any."""

    @abstractmethod
    def get_original_error(self, error: Exception, /) -> BaseException | None:
        """Returns the original error of an exception if available.

        Whatever exception is returned here will be used for logging
        the traceback. If None is returned, ``error`` is logged instead.

        """

    @abstractmethod
    async def send(self, ctx: T, content: str, /) -> None:
        """Sends a response to the command invoker."""

    @abstractmethod
    def should_handle(self, ctx: T, error: Exception, /) -> bool:
        """Checks if the given error should be handled."""

    async def handle(self, ctx: T, error: Exception, /) -> None:
        if not self.should_handle(ctx, error):
            return

        error_code = generate_error_code()

        for resp in self.responses:
            if isinstance(error, resp.exc_types):
                content = await resp.format(ctx, error)
                break
        else:
            raise ValueError(f"Unable to handle exception: {error!r}")

        if resp.show_traceback:
            self._log_error(ctx, error, error_code)

        if content is not None:
            if resp.show_traceback:
                content = await append_error_code(ctx, content, error_code)
            await self.send(ctx, content)

    def _log_error(self, ctx: T, error: Exception, error_code: str) -> None:
        error_name = type(error).__name__
        command = self.get_command_name(ctx) or "no command"
        original = self.get_original_error(error) or error

        log.error(
            f'{error_name} while invoking "{command}" (code: {error_code})',
            exc_info=original,
        )


class PrefixErrorHandler(ErrorHandler[Context]):
    responses = [
        ErrorResponse(
            (commands.CommandNotFound, commands.DisabledCommand),
            content=None,
            show_traceback=False,
        ),
        ErrorResponse(
            commands.CommandOnCooldown,
            # Error response for command on cooldown
            # {0}: an exception containing the duration to wait in .retry_after
            _("This command is on cooldown for {0.retry_after:.1f}s."),
            show_traceback=False,
        ),
        ErrorResponse(
            commands.MaxConcurrencyReached,
            # Error response for exceeding maximum concurrent users of a command
            _("Too many people are using this command. Please try again later."),
            show_traceback=False,
        ),
        ErrorResponse(
            commands.CheckFailure,
            # Error response for not passing all checks required to use a command
            _("One or more checks failed for this command."),
            show_traceback=False,
        ),
        ErrorResponse(
            commands.UserInputError,
            # Error response for failing to parse the user's input
            # {0}: the error description
            _("An error occurred with your input: ```py\n{0}```"),
            show_traceback=True,
        ),
        ErrorResponse(
            Exception,
            # Error response for an unexpected failure in a command
            _("An unknown error occurred while running this command."),
            show_traceback=True,
        ),
    ]

    def get_command_name(self, ctx: Context) -> str | None:
        if ctx.command is not None:
            return ctx.command.qualified_name

    def get_original_error(self, error: Exception) -> BaseException | None:
        if isinstance(error, (commands.CommandInvokeError, commands.ConversionError)):
            return error.original
        elif isinstance(error, commands.HybridCommandError):
            return TreeErrorHandler().get_original_error(error)

    async def send(self, ctx: Context, content: str) -> None:
        await ctx.send(
            content,
            allowed_mentions=discord.AllowedMentions.none(),
            ephemeral=True,
        )

    def should_handle(self, ctx: Context, error: Exception, /) -> bool:
        return not getattr(ctx, "handled", False)


class TreeErrorHandler(ErrorHandler[discord.Interaction]):
    responses = [
        AppCommandErrorResponse(show_traceback=False),
        ErrorResponse(
            app_commands.CommandOnCooldown,
            # Error response for command on cooldown
            # {0}: an exception containing the duration to wait in .retry_after
            _("This command is on cooldown for {0.retry_after:.1f}s."),
            show_traceback=False,
        ),
        ErrorResponse(
            app_commands.CheckFailure,
            # Error response for not passing all checks required to use a command
            _("One or more checks failed for this command."),
            show_traceback=False,
        ),
        ErrorResponse(
            app_commands.TransformerError,
            # Error response for failing to parse the user's input
            # {0}: the error description
            _("An error occurred with your input: ```py\n{0}```"),
            show_traceback=True,
        ),
        ErrorResponse(
            app_commands.CommandNotFound,
            # Error response for using a slash command not recognized by the bot
            _("The bot currently does not recognize this command."),
            show_traceback=True,
        ),
        ErrorResponse(
            Exception,
            # Error response for an unexpected failure in a command
            _("An unknown error occurred while running this command."),
            show_traceback=True,
        ),
    ]

    def get_command_name(self, interaction: discord.Interaction) -> str | None:
        if interaction.command is not None:
            return "/" + interaction.command.qualified_name

    def get_original_error(self, error: Exception) -> BaseException | None:
        if isinstance(error, app_commands.CommandInvokeError):
            return error.original
        elif isinstance(error, app_commands.TransformerError):
            return error.__cause__

    async def send(self, interaction: discord.Interaction, content: str) -> None:
        kwargs = {
            "content": content,
            "allowed_mentions": discord.AllowedMentions.none(),
            "ephemeral": True,
        }
        if interaction.response.is_done():
            await interaction.followup.send(**kwargs)
        else:
            await interaction.response.send_message(**kwargs)

    def should_handle(
        self,
        interaction: discord.Interaction,
        error: Exception,
        /,
    ) -> bool:
        return not interaction.extras.get("handled", False)


class Errors(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.prefix_handler = PrefixErrorHandler()
        self.tree_handler = TreeErrorHandler()
        self.setup_events()

    async def cog_unload(self):
        self.teardown_events()

    def setup_events(self):
        self._old_command_error = self.bot.on_command_error
        self.bot.on_command_error = self.prefix_handler.handle  # type: ignore

        self._old_tree_error = self.bot.tree.on_error
        self.bot.tree.error(self.tree_handler.handle)

    def teardown_events(self):
        self.bot.on_command_error = self._old_command_error
        self.bot.tree.error(self._old_tree_error)  # type: ignore


async def setup(bot: Bot):
    await bot.add_cog(Errors(bot))
