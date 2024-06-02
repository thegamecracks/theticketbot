import discord
from discord import app_commands
from discord.ext import commands

from theticketbot.bot import Bot, Context


def count_localizations(command: app_commands.AppCommand) -> int:
    """Returns the number of localizations defined for a command.

    .. seealso::

        https://discord.com/developers/docs/interactions/application-commands#application-command-object

    """
    n = 0
    n += len(command.name_localizations)
    n += len(command.description_localizations)
    for option in command.options:
        n += len(option.name_localizations)
        n += len(option.description_localizations)
        if not isinstance(option, app_commands.AppCommandGroup):
            n += sum(len(choice.name_localizations) for choice in option.choices)
    return n


class Owner(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def cog_check(self, ctx: Context):  # type: ignore  # async is allowed
        return await commands.is_owner().predicate(ctx)

    @commands.command(name="reload-config", aliases=["config-reload"])
    async def reload_config(self, ctx: Context):
        """Reload the bot's configuration."""
        self.bot.refresh_config()
        await ctx.reply("Config reloaded!")

    @commands.command(name="sync")
    async def sync(self, ctx: Context, guild_id: int | None = None):
        """Synchronize the bot's application commands."""
        guild: discord.Object | None = None
        if guild_id is not None:
            guild = discord.Object(guild_id)

        commands = await ctx.bot.tree.sync(guild=guild)
        n_commands = len(commands)
        n_localizations = sum(map(count_localizations, commands))
        await ctx.send(
            f"{n_commands} command(s) synchronized "
            f"with a total of {n_localizations} localizations!"
        )


async def setup(bot: Bot):
    await bot.add_cog(Owner(bot))
