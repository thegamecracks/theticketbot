import discord

from .errors import AppCommandResponse


class View(discord.ui.View):
    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ) -> None:
        if not isinstance(error, AppCommandResponse):
            return await super().on_error(interaction, error, item)

        content = await error.translate(interaction)
        if interaction.response.is_done():
            await interaction.followup.send(content, ephemeral=True)
        else:
            await interaction.response.send_message(content, ephemeral=True)
