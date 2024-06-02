import time
from dataclasses import dataclass, field

import discord
from discord import app_commands
from discord.app_commands import locale_str as _
from discord.ext import commands, tasks

from theticketbot.bot import Bot
from theticketbot.translator import translate


@dataclass
class SelectedMessages:
    timestamp: float = 0
    messages: list[discord.Message] = field(default_factory=list)


class Select(commands.Cog):
    CLEANUP_INTERVAL = 60
    MESSAGE_EXPIRES_AFTER = 180
    MAX_SELECTED_MESSAGES = 3

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

        self._selected_messages: dict[int, SelectedMessages] = {}
        self.cleanup_loop.start()

    def get_selected_messages(self, user_id: int) -> list[discord.Message]:
        """Return a list of messages recently selected by a user."""
        queue = self._selected_messages.get(user_id)
        if queue is None:
            return []

        return queue.messages.copy()

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
        queue = self._selected_messages.setdefault(
            interaction.user.id,
            SelectedMessages(),
        )
        queue.timestamp = time.monotonic()

        if len(queue.messages) < self.MAX_SELECTED_MESSAGES:
            queue.messages.append(message)

            # Message sent when the user selects a message
            # {0}: the selected message's link
            # {1}: the total number of messages selected
            # {2}: the time until the selected message is discarded
            content = _(
                "{0}\nMessage #{1} selected! You have {2} seconds to perform "
                "an action with this message."
            )
        else:
            queue.messages.clear()
            queue.messages.append(message)

            # Message sent when the user has selected too many messages
            # {0}: the selected message's link
            # {1}: the total number of messages selected
            # {2}: the time until the selected message is discarded
            content = _(
                "{0}\nYou have selected too many messages! This is now message #{1}."
            )

        content = await translate(content, interaction)
        content = content.format(
            message.jump_url,
            len(queue.messages),
            self.MESSAGE_EXPIRES_AFTER,
        )
        await interaction.response.send_message(content, ephemeral=True)

    @tasks.loop(seconds=CLEANUP_INTERVAL)
    async def cleanup_loop(self) -> None:
        now = time.monotonic()

        to_remove: list[int] = []
        for user_id, queue in self._selected_messages.items():
            if now > queue.timestamp + self.MESSAGE_EXPIRES_AFTER:
                to_remove.append(user_id)

        for user_id in to_remove:
            del self._selected_messages[user_id]


async def setup(bot: Bot):
    await bot.add_cog(Select(bot))
