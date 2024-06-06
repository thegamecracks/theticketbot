import datetime
import logging
import discord
from discord.ext import commands, tasks

from theticketbot.bot import Bot

log = logging.getLogger(__name__)


class Cleanup(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.cleanup_loop.start()

    # @commands.Cog.listener("on_guild_remove")
    # async def remove_guild(self, guild: discord.Guild):
    #     async with self.bot.acquire() as conn:
    #         await conn.execute("DELETE FROM guild WHERE id = ?", guild.id)
    #
    # In case the bot is unintentionally kicked, retain all tickets
    # until the next cleanup cycle

    @commands.Cog.listener("on_guild_channel_delete")
    async def remove_guild_channel(self, channel: discord.abc.GuildChannel):
        async with self.bot.acquire() as conn:
            await conn.execute("DELETE FROM channel WHERE id = ?", channel.id)

    @commands.Cog.listener("on_raw_thread_delete")
    async def remove_thread(self, payload: discord.RawThreadDeleteEvent):
        async with self.bot.acquire() as conn:
            await conn.execute("DELETE FROM channel WHERE id = ?", payload.thread_id)

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

    @tasks.loop(time=datetime.time(0, 0, tzinfo=datetime.timezone.utc))
    async def cleanup_loop(self) -> None:
        now = datetime.datetime.now(datetime.timezone.utc)
        if now.weekday() != 5:
            return

        await self.cleanup_guilds()

    async def cleanup_guilds(self) -> None:
        guild_ids = {guild.id for guild in self.bot.guilds}
        async with self.bot.acquire() as conn:
            rows = await conn.fetchall("SELECT id FROM guild")
            rows = {row[0] for row in rows}
            rows = rows - guild_ids
            rows = [(guild_id,) for guild_id in rows]
            await conn.executemany("DELETE FROM guild WHERE id = ?", rows)

        if len(rows) > 0:
            log.info("%d guilds cleaned up", rows)

    # NOTE: users are not removed by any event
    # NOTE: members are not removed by any event, members intent required
    # NOTE: rows can still accumulate during bot downtime


async def setup(bot: Bot):
    await bot.add_cog(Cleanup(bot))
