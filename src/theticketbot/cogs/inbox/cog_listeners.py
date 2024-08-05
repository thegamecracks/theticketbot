import logging

import discord
import discord.http
from discord.ext import commands

from theticketbot.bot import Bot
from theticketbot.translator import locale_str as _, translate

log = logging.getLogger(__name__)


class InboxListeners(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener("on_raw_thread_member_remove")
    async def on_ticket_owner_remove(self, payload: discord.RawThreadMembersUpdate):
        # NOTE: event may not fire on already-archived tickets
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return log.warning("Ignoring unknown guild %d", payload.guild_id)

        thread = guild.get_thread(payload.thread_id)
        if thread is None:
            return log.warning("Ignoring unknown thread %d", payload.thread_id)

        if thread.owner_id != guild.me.id:
            return

        user_ids = set(map(int, payload.data.get("removed_member_ids", ())))

        async with self.bot.acquire() as conn:
            row = await conn.fetchone(
                "SELECT owner_id FROM ticket WHERE id = ?",
                payload.thread_id,
            )
            if row is None:
                return

        owner_id: int = row[0]
        if owner_id not in user_ids:
            return

        content = await translate(
            _("ticket-archived-owner-left"),
            self.bot,
            locale=guild.preferred_locale,
            data={"owner": f"<@{owner_id}>"},
        )
        await self.archive_ticket_with_message(thread, content)

    @commands.Cog.listener("on_raw_member_remove")
    async def on_ticket_owner_remove_guild(self, payload: discord.RawMemberRemoveEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return log.warning("Ignoring unknown guild %d", payload.guild_id)

        async with self.bot.acquire() as conn:
            rows = await conn.fetchall(
                "SELECT ticket.id FROM ticket "
                "JOIN inbox ON inbox.id = inbox_id "
                "JOIN message ON message.id = inbox.id "
                "JOIN channel ON channel.id = channel_id "
                "JOIN guild ON guild.id = guild_id "
                "WHERE guild_id = ? AND owner_id = ?",
                payload.guild_id,
                payload.user.id,
            )

        for (ticket_id,) in rows:
            thread = guild.get_thread(ticket_id)
            if thread is None:
                log.warning("Ignoring unknown thread %d", ticket_id)
                continue

            content = await translate(
                _("ticket-archived-owner-left-guild"),
                self.bot,
                locale=guild.preferred_locale,
                data={"owner": payload.user.mention},
            )
            await self.archive_ticket_with_message(thread, content)

    async def archive_ticket_with_message(
        self,
        thread: discord.Thread,
        content: str,
    ) -> None:
        can_lock = thread.permissions_for(thread.guild.me).manage_threads
        await thread.send(content, allowed_mentions=discord.AllowedMentions.none())
        await thread.edit(archived=True, locked=can_lock)

    @commands.Cog.listener("on_raw_thread_update")
    async def lock_archived_tickets(self, payload: discord.RawThreadUpdateEvent):
        guild_id = payload.guild_id
        thread_id = payload.thread_id

        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return log.warning("Ignoring unknown guild %d", guild_id)

        if int(payload.data["owner_id"]) != guild.me.id:
            return

        thread_metadata = payload.data["thread_metadata"]
        if not thread_metadata["archived"] or thread_metadata.get("locked"):
            return

        channel_id = int(payload.data["parent_id"])
        channel = guild.get_channel(channel_id)
        if channel is None:
            return log.warning(
                "Ignoring unknown parent %d for thread %d",
                channel_id,
                thread_id,
            )

        permissions = channel.permissions_for(guild.me)
        if not permissions.manage_threads:
            return

        async with self.bot.acquire() as conn:
            row = await conn.fetchone("SELECT 1 FROM ticket WHERE id = ?", thread_id)
            if row is None:
                return

        content = await translate(
            _("ticket-archived-lock"),
            self.bot,
            locale=guild.preferred_locale,
        )

        params = discord.http.handle_message_parameters(content)
        await self.bot.http.send_message(thread_id, params=params)
        await self.bot.http.edit_channel(thread_id, archived=True, locked=True)
