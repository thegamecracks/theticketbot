from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asqlite

INBOX_STAFF_MENTION_PATTERN = re.compile(r"<@\d+>|<@&\d+>")


class DatabaseClient:
    """Provides an API for making common queries with an :class:`asqlite.Connection`."""

    def __init__(self, conn: asqlite.Connection) -> None:
        self.conn = conn

    # User methods

    async def add_user(self, user_id: int) -> None:
        """Add a user to the database.

        Existing users are ignored.

        """
        await self.conn.execute("INSERT OR IGNORE INTO user (id) VALUES (?)", user_id)

    # Guild methods

    async def add_guild(self, guild_id: int) -> None:
        """Add a guild to the database.

        Existing guilds are ignored.

        """
        await self.conn.execute("INSERT OR IGNORE INTO guild (id) VALUES (?)", guild_id)

    # Member methods

    async def add_member(self, user_id: int, guild_id: int) -> None:
        """Add a member to the database.

        Existing members and guilds are ignored.

        """
        await self.add_user(user_id)
        await self.add_guild(guild_id)
        await self.conn.execute(
            "INSERT OR IGNORE INTO member (guild_id, user_id) VALUES (?, ?)",
            guild_id,
            user_id,
        )

    async def add_user_or_member(
        self,
        user_id: int,
        *,
        guild_id: int | None = None,
    ) -> None:
        """Add a user/member to the database.

        Existing users, members, and guilds are ignored.

        """
        if guild_id is None:
            await self.add_user(user_id)
        else:
            await self.add_member(user_id, guild_id)

    # Channel methods

    async def add_channel(
        self,
        channel_id: int,
        *,
        guild_id: int | None = None,
    ) -> None:
        """Add a channel to the database.

        Existing channels and guilds are ignored.

        """
        if guild_id is not None:
            await self.add_guild(guild_id)

        await self.conn.execute(
            "INSERT OR IGNORE INTO channel (id, guild_id) VALUES (?, ?)",
            channel_id,
            guild_id,
        )

    # Message methods

    async def add_message(
        self,
        message_id: int,
        channel_id: int,
        *,
        guild_id: int | None = None,
    ) -> None:
        """Add a message to the database.

        Existing messages, channels, and guilds are ignored.

        """
        await self.add_channel(channel_id, guild_id=guild_id)
        await self.conn.execute(
            "INSERT OR IGNORE INTO message (id, channel_id) VALUES (?, ?)",
            message_id,
            channel_id,
        )

    # Inbox methods

    async def add_inbox(
        self,
        message_id: int,
        channel_id: int,
        *,
        guild_id: int | None = None,
    ) -> None:
        """Add an inbox to the database.

        :raises sqlite3.IntegrityError: The inbox already exists.

        """
        await self.add_message(message_id, channel_id, guild_id=guild_id)
        await self.conn.execute("INSERT INTO inbox (id) VALUES (?)", message_id)

    async def get_inbox_starter_content(self, inbox_id: int) -> str:
        """Get the starter content for an inbox.

        :returns: The starter content, if any.

        """
        row = await self.conn.fetchone(
            "SELECT starter_content FROM inbox WHERE id = ?",
            inbox_id,
        )
        assert row is not None
        return row[0]

    async def set_inbox_starter_content(
        self,
        inbox_id: int,
        starter_content: str,
    ) -> None:
        """Set the starter content for an inbox."""
        await self.conn.execute(
            "UPDATE inbox SET starter_content = ? WHERE id = ?",
            starter_content,
            inbox_id,
        )

    async def add_inbox_staff(self, inbox_id: int, mention: str) -> None:
        """Add an inbox staff to the database.

        :raises ValueError:
            The mention string does not match a user or role format.
        :raises sqlite3.IntegrityError:
            Either the inbox does not exist or the mention already exists.

        """
        if not INBOX_STAFF_MENTION_PATTERN.fullmatch(mention):
            raise ValueError(f"Invalid user/role mention: {mention!r}")

        await self.conn.execute(
            "INSERT INTO inbox_staff (inbox_id, mention) VALUES (?, ?)",
            inbox_id,
            mention,
        )

    async def get_inbox_staff(self, inbox_id: int) -> list[str]:
        """Get all staff mentions for an inbox.

        If the inbox does not exist, an empty list is returned.

        :returns: A list of staff mentions.

        """
        rows = await self.conn.fetchall(
            "SELECT mention FROM inbox_staff WHERE inbox_id = ?",
            inbox_id,
        )
        return [row[0] for row in rows]

    async def remove_inbox_staff(self, inbox_id: int, mention: str) -> bool:
        """Remove an inbox staff from the database.

        :returns: True if the given inbox staff existed, False otherwise.

        """
        row = await self.conn.fetchone(
            "DELETE FROM inbox_staff WHERE inbox_id = ? AND mention = ? RETURNING 1",
            inbox_id,
            mention,
        )
        return row is not None

    # Ticket methods

    async def add_ticket(
        self,
        *,
        ticket_id: int,
        inbox_id: int,
        owner_id: int,
        guild_id: int,
    ) -> None:
        """Add a ticket to the database.

        :raises sqlite3.IntegrityError: The ticket already exists.

        """
        await self.add_member(owner_id, guild_id)
        await self.add_channel(ticket_id, guild_id=guild_id)
        await self.add_channel(inbox_id, guild_id=guild_id)
        await self.conn.execute(
            "INSERT INTO ticket (id, inbox_id, owner_id) VALUES (?, ?, ?)",
            ticket_id,
            inbox_id,
            owner_id,
        )

    async def count_matching_tickets(self, ticket_ids: list[int]) -> int:
        """Count the number of ticket IDs that exist in the database."""
        placeholders = ", ".join("?" * len(ticket_ids))
        row = await self.conn.fetchone(
            f"SELECT COUNT(*) FROM ticket WHERE id IN ({placeholders})",
            *ticket_ids,
        )
        assert row is not None
        return row[0]
