from __future__ import annotations

import contextlib
import importlib.metadata
import logging
import sqlite3
import sys
from enum import Flag, auto
from typing import TYPE_CHECKING, AsyncGenerator, Callable, cast

import asqlite
import discord
from discord.ext import commands
from pydantic import SecretStr

from . import database
from .migrations import run_default_migrations
from .translator import GettextTranslator

if TYPE_CHECKING:
    from .cogs.select import MessageCallback, Select
    from .config import Settings

log = logging.getLogger(__name__)


class StartupFlags(Flag):
    SYNC = auto()
    CLOSE = auto()


# https://discordpy.readthedocs.io/en/stable/ext/commands/api.html
class Bot(commands.Bot):
    key_pragma: SecretStr | None
    """The key pragma to append onto the database pragmas.

    This should be assigned after construction.

    """

    def __init__(
        self,
        config_refresher: Callable[[], Settings],
        *,
        startup_flags: StartupFlags,
    ):
        self._config_refresher = config_refresher
        config = self.refresh_config()

        self.startup_flags = startup_flags
        self.key_pragma = None

        super().__init__(
            chunk_guilds_at_startup=False,
            command_prefix=commands.when_mentioned,
            intents=config.bot.intents.create_intents(),
            member_cache_flags=discord.MemberCacheFlags.none(),
            strip_after_prefix=True,
        )

    @contextlib.asynccontextmanager
    async def acquire(
        self,
        *,
        transaction: bool = True,
    ) -> AsyncGenerator[asqlite.Connection, None]:
        """Acquire a connection to the database.

        :param transaction: If True, a transaction is opened as well.

        """
        path = str(self.config.db.path)
        init = lambda conn: self._run_config_pragmas(conn)
        async with database.connect(path, init=init) as conn:
            if not transaction:
                yield conn
            else:
                async with conn.transaction():
                    yield conn

    def _run_config_pragmas(self, conn: sqlite3.Connection) -> None:
        pragmas = [p.get_secret_value() for p in self.config.db.pragmas]
        if self.key_pragma is not None:
            pragmas.append(self.key_pragma.get_secret_value())
        conn.executescript(";\n".join(pragmas))

    def set_message_callback(
        self,
        guild_id: int,
        user_id: int,
        callback: MessageCallback,
    ) -> None:
        """Set the next message callback for the given user."""
        cog = cast("Select | None", self.get_cog("Select"))
        if cog is None:
            return log.warning(
                "Cannot set message callback for %d, Select cog not loaded",
                user_id,
            )

        return cog.set_message_callback(guild_id, user_id, callback)

    async def _maybe_load_jishaku(self) -> None:
        if not self.config.bot.allow_jishaku:
            return

        try:
            version = importlib.metadata.version("jishaku")
        except importlib.metadata.PackageNotFoundError:
            pass
        else:
            await self.load_extension("jishaku")
            log.info("Loaded jishaku extension (version: %s)", version)

    def refresh_config(self) -> Settings:
        config = self._config_refresher()
        self.config = config
        return config

    async def setup_hook(self) -> None:
        self.config.db.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.config.db.path) as conn:
            self._run_config_pragmas(conn)
            run_default_migrations(conn)

        for path in self.config.bot.extensions:
            await self.load_extension(path, package=__package__)
        log.info("Loaded %d extensions", len(self.config.bot.extensions))
        await self._maybe_load_jishaku()

        await self.tree.set_translator(GettextTranslator())

        if self.startup_flags & StartupFlags.SYNC:
            commands = await self.tree.sync()
            log.info("Synced %d application commands", len(commands))

        if self.startup_flags & StartupFlags.CLOSE:
            sys.exit()


class Context(commands.Context[Bot]): ...
