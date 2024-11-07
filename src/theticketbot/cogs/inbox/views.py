import re
import string
from typing import Awaitable, Callable, Iterable

import asqlite
import discord
from discord.app_commands import locale_str

from theticketbot.bot import Bot
from theticketbot.database import DatabaseClient
from theticketbot.translator import locale_str as _, translate
from theticketbot.views import View

from .constants import DEFAULT_STARTER_CONTENT, DEFAULT_TICKET_NAME
from .destination import get_inbox_destination
from .staff import get_and_filter_inbox_staff

MENTION_PATTERN = re.compile(r"<(@|@&)(\d+)>")

InboxRatelimit = Callable[[discord.Message, discord.Member], Awaitable[float]]


def mention_to_snowflake(mention: str) -> discord.Object:
    m = MENTION_PATTERN.fullmatch(mention)
    if m is None:
        raise ValueError(f"Invalid user/role mention: {mention!r}")

    if m[1] == "@":
        return discord.Object(int(m[2]), type=discord.User)
    elif m[1] == "@&":
        return discord.Object(int(m[2]), type=discord.Role)
    raise ValueError(f"Unsupported mention type {m[1]!r}")


class InboxView(View):
    def __init__(self, bot: Bot, ratelimit_check: InboxRatelimit) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.ratelimit_check = ratelimit_check

    async def localize(self, locale: discord.Locale) -> None:
        async def t(s: locale_str) -> str:
            return await translate(s, self.bot, locale=locale)

        # Button label for creating a new ticket
        self.create_ticket.label = await t(_("inbox-ticket-button"))

    @discord.ui.button(custom_id="create-ticket", style=discord.ButtonStyle.primary)
    async def create_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        # FIXME: this function is too big, can we do any better?
        assert isinstance(interaction.channel, discord.TextChannel)
        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None
        assert interaction.message is not None

        guild = interaction.guild
        message = interaction.message

        async with self.bot.acquire() as conn:
            # If the database was wiped, this will fail.
            row = await conn.fetchone("SELECT 1 FROM inbox WHERE id = ?", message.id)
            if row is None:
                content = await translate(_("inbox-ticket-unknown"), interaction)
                return await interaction.response.send_message(content, ephemeral=True)

            tickets = await self.get_active_user_tickets(
                interaction.channel.threads,
                conn,
                message.id,
                interaction.user.id,
            )
            tickets.sort(key=lambda t: t.id)
            max_tickets = await self.get_max_tickets(conn, message.id)

        if max_tickets > 0 and len(tickets) >= max_tickets:
            content = await translate(
                _("inbox-ticket-max-per-user"),
                interaction,
                data={"ticket": tickets[-1].jump_url},
            )
            return await interaction.response.send_message(content, ephemeral=True)

        retry_after = await self.ratelimit_check(message, interaction.user)
        if retry_after > 0:
            content = await translate(
                _("inbox-ticket-on-cooldown"),
                interaction,
                data={"duration": retry_after},
            )
            return await interaction.response.send_message(content, ephemeral=True)

        # Message sent when creating a ticket
        content = await translate(_("inbox-ticket-creating"), interaction)
        await interaction.response.send_message(content, ephemeral=True)

        async with self.bot.acquire() as conn:
            query = DatabaseClient(conn)
            destination = await get_inbox_destination(query, interaction.guild, message)
            ticket_name = await query.get_inbox_default_ticket_name(message.id)
            ticket_name = ticket_name or DEFAULT_TICKET_NAME

            # NOTE: counter may skip if thread creation fails
            counter = await query.increment_inbox_counter(message.id)

        created_at = interaction.created_at
        ticket_name = string.Template(ticket_name).safe_substitute(
            year=created_at.year,
            month=str(created_at.month).zfill(2),
            day=str(created_at.day).zfill(2),
            author=interaction.user.display_name,
            counter=str(counter % 10**4).zfill(4),
        )

        reason = await translate(
            _("inbox-ticket-creating-reason"),
            interaction,
            locale=guild.preferred_locale,
            data={"owner": interaction.user.name},
        )

        try:
            ticket = await destination.create_thread(
                name=ticket_name[:100],
                invitable=False,
                reason=reason,
            )

            async with self.bot.acquire() as conn:
                query = DatabaseClient(conn)
                await query.add_ticket(
                    ticket_id=ticket.id,
                    inbox_id=message.id,
                    owner_id=interaction.user.id,
                    guild_id=guild.id,
                )

            async with self.bot.acquire() as conn:
                query = DatabaseClient(conn)
                mentions = await get_and_filter_inbox_staff(query, guild, message.id)
                mentions = " ".join(mentions)

                starter_content = await query.get_inbox_starter_content(message.id)
                starter_content = starter_content or DEFAULT_STARTER_CONTENT

            content = string.Template(starter_content).safe_substitute(
                author=interaction.user.mention,
                staff=mentions,
            )
            await ticket.send(content[:2000])
        except discord.Forbidden:
            content = _("inbox-ticket-error-insufficient-bot-permissions")
            content = await translate(content, interaction)
            return await interaction.edit_original_response(content=content)
        except Exception:
            content = await translate(_("inbox-ticket-error-unknown"), interaction)
            await interaction.edit_original_response(content=content)
            raise
        else:
            content = await translate(
                _("inbox-ticket-finished"),
                interaction,
                data={"ticket": ticket.jump_url},
            )
            await interaction.edit_original_response(content=content)

    async def get_active_user_tickets(
        self,
        threads: Iterable[discord.Thread],
        conn: asqlite.Connection,
        inbox_id: int,
        owner_id: int,
    ) -> list[discord.Thread]:
        # Should do an intersect here, but this should be small enough
        c = await conn.execute(
            "SELECT id FROM ticket WHERE inbox_id = ? AND owner_id = ?",
            inbox_id,
            owner_id,
        )
        ticket_ids: set[int] = {row[0] for row in await c.fetchall()}

        members_intent = self.bot.intents.members
        active: list[discord.Thread] = []
        for t in threads:
            if t.id not in ticket_ids:
                continue
            if members_intent and discord.utils.get(t.members, id=owner_id) is None:
                continue
            active.append(t)
        return active

    async def get_max_tickets(self, conn: asqlite.Connection, inbox_id: int) -> int:
        row = await conn.fetchone(
            "SELECT max_tickets_per_user FROM inbox WHERE id = ?",
            inbox_id,
        )
        assert row is not None
        return row[0]


class InboxStaffView(View):
    def __init__(self, bot: Bot, inbox_id: int, staff: set[str]) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.inbox_id = inbox_id
        self.staff = staff
        self.refresh()

    def refresh(self) -> None:
        staff = [mention_to_snowflake(staff) for staff in self.staff]
        self.on_staff_select.default_values = staff

    @discord.ui.select(cls=discord.ui.MentionableSelect, min_values=0, max_values=10)
    async def on_staff_select(
        self,
        interaction: discord.Interaction,
        select: discord.ui.MentionableSelect,
    ):
        ordered_mentions = [m.mention for m in select.values]
        mentions = set(ordered_mentions)
        added = mentions - self.staff
        removed = self.staff - mentions

        if len(added) == 0 and len(removed) == 0:
            content = await translate(_("inbox-staff-no-edits"), interaction)
            return await interaction.response.send_message(content, ephemeral=True)

        async with self.bot.acquire() as conn:
            query = DatabaseClient(conn)
            for mention in added:
                await query.add_inbox_staff(self.inbox_id, mention)
            for mention in removed:
                await query.remove_inbox_staff(self.inbox_id, mention)

        self.staff = mentions
        await interaction.response.defer()
