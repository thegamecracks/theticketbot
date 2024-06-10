import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import discord
from discord import app_commands
from discord.app_commands import locale_str as _
from discord.ext import commands, tasks

from theticketbot.bot import Bot
from theticketbot.translator import translate

MessageCallback = Callable[[discord.Interaction, discord.Message], Awaitable[Any]]


@dataclass
class MessageCommand:
    timestamp: float
    callback: MessageCallback


class Select(commands.Cog):
    CLEANUP_INTERVAL = 60
    CLEANUP_EXPIRED_AFTER = 300
    MESSAGE_EXPIRES_AFTER = 180

    def __init__(self, bot: Bot):
        self.bot = bot
        self.cog_menus = (
            app_commands.ContextMenu(
                # Command name
                name=_("Select this message"),
                callback=self.on_message_selected,
            ),
        )

        for menu in self.cog_menus:
            bot.tree.add_command(menu)

        self._message_commands: dict[tuple[int, int], MessageCommand] = {}
        self.cleanup_loop.start()

    def set_message_callback(
        self,
        guild_id: int,
        user_id: int,
        callback: MessageCallback,
    ) -> None:
        """Set the next message callback for the given user."""
        key = (guild_id, user_id)
        self._message_commands[key] = MessageCommand(time.monotonic(), callback)

    async def cog_unload(self) -> None:
        for menu in self.cog_menus:
            self.bot.tree.remove_command(menu.name, type=menu.type)

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def on_message_selected(
        self,
        interaction: discord.Interaction,
        message: discord.Message,
    ):
        assert interaction.guild is not None
        key = (interaction.guild.id, interaction.user.id)
        command = self._message_commands.get(key)

        if command is None:
            content = _(
                # Message sent when selecting a message without a command
                "You can't select a message right now! "
                "Please use a command that asks for a message first."
            )
            content = await translate(content, interaction)
            return await interaction.response.send_message(content, ephemeral=True)
        elif time.monotonic() > command.timestamp + self.MESSAGE_EXPIRES_AFTER:
            content = _(
                # Message sent when selecting a message too long after their last command
                "Sorry, your last command has expired. "
                "Please use a command again and then select this message."
            )
            content = await translate(content, interaction)
            return await interaction.response.send_message(content, ephemeral=True)

        del self._message_commands[key]
        try:
            await command.callback(interaction, message)
        except BaseException:
            command.timestamp = time.monotonic()
            self._message_commands.setdefault(key, command)
            raise

    @tasks.loop(seconds=CLEANUP_INTERVAL)
    async def cleanup_loop(self) -> None:
        now = time.monotonic()

        to_remove: list[tuple[int, int]] = []
        cleanup_after = self.MESSAGE_EXPIRES_AFTER + self.CLEANUP_EXPIRED_AFTER
        for key, queue in self._message_commands.items():
            if now > queue.timestamp + cleanup_after:
                to_remove.append(key)

        for key in to_remove:
            del self._message_commands[key]


async def setup(bot: Bot):
    await bot.add_cog(Select(bot))
