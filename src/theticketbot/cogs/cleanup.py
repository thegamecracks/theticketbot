import discord
from discord.ext import commands

from theticketbot.bot import Bot


class Cleanup(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    # @commands.Cog.listener("on_guild_remove")
    # async def remove_guild(self, guild: discord.Guild):
    #     async with self.bot.acquire() as conn:
    #         await conn.execute("DELETE FROM guild WHERE id = ?", guild.id)
    #
    # In case the bot is unintentionally kicked, retain all tickets

    @commands.Cog.listener("on_guild_channel_delete")
    async def remove_guild_channel(self, channel: discord.abc.GuildChannel):
        async with self.bot.acquire() as conn:
            await conn.execute("DELETE FROM channel WHERE id = ?", channel.id)

    @commands.Cog.listener("on_raw_message_delete")
    async def remove_message(self, payload: discord.RawMessageDeleteEvent):
        async with self.bot.acquire() as conn:
            await conn.execute("DELETE FROM message WHERE id = ?", payload.message_id)

    @commands.Cog.listener("on_raw_bulk_message_delete")
    async def bulk_remove_messages(self, payload: discord.RawBulkMessageDeleteEvent):
        async with self.bot.acquire() as conn:
            await conn.executemany(
                "DELETE FROM message WHERE id = ?",
                [(id,) for id in payload.message_ids],
            )

    # NOTE: users are not removed by any event
    # NOTE: members are not removed by any event, members intent required
    # NOTE: rows can still accumulate during bot downtime


async def setup(bot: Bot):
    await bot.add_cog(Cleanup(bot))
