from typing import Any

import discord
from discord import app_commands

from .translator import translate


class AppCommandResponse(app_commands.AppCommandError):
    """An exception used for sending a message directly to the user.

    Parameters
    ----------
    message: str | app_commands.locale_str
        The message to be shown to the user. Can be a localized string.
    data: Any
        If message is a localized string, this data will be passed to
        the bot's translator.

    """

    def __init__(
        self,
        message: str | app_commands.locale_str,
        data: Any = None,
    ) -> None:
        super().__init__(str(message))
        self.message = message
        self.data = data

    async def translate(self, interaction: discord.Interaction) -> str:
        if isinstance(self.message, str):
            return self.message

        return await translate(self.message, interaction, data=self.data)
