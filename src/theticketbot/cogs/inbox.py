from __future__ import annotations

import functools
import logging
import re
import string
import time
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Iterable,
    Sequence,
    TypedDict,
    cast,
)

import asqlite
import discord
import discord.http
import humanize
from discord import app_commands
from discord.app_commands import locale_str as _
from discord.ext import commands, tasks

from theticketbot.bot import Bot
from theticketbot.database import DatabaseClient
from theticketbot.errors import AppCommandResponse
from theticketbot.translator import translate

if TYPE_CHECKING:
    from .select import MessageCallback

DEFAULT_STARTER_CONTENT = "$author $staff"
DEFAULT_TICKET_NAME = "$year-$month-$day $author"
MENTION_PATTERN = re.compile(r"<(@|@&)(\d+)>")

InboxRatelimit = Callable[[discord.Message, discord.Member], Awaitable[float]]

log = logging.getLogger(__name__)


class InboxView(discord.ui.View):
    def __init__(self, bot: Bot, ratelimit_check: InboxRatelimit) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.ratelimit_check = ratelimit_check

    async def localize(self, locale: discord.Locale) -> None:
        async def t(s: _) -> str:
            return await translate(s, self.bot, locale=locale)

        # Button label for creating a new ticket
        self.create_ticket.label = await t(_("Create Ticket"))

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
                content = _(
                    # Message sent when an inbox is not recognized
                    "Sorry, this inbox is no longer recognized and must be "
                    "re-created. Please notify a server admin!"
                )
                content = await translate(content, interaction)
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
            content = _(
                # Message sent when trying to create too many tickets
                # {0}: the ticket's link
                "You have too many tickets in this inbox. "
                "Please close your last ticket {0} before creating a new one."
            )
            content = await translate(content, interaction)
            content = content.format(tickets[-1].jump_url)
            return await interaction.response.send_message(content, ephemeral=True)

        retry_after = await self.ratelimit_check(message, interaction.user)
        if retry_after > 0:
            # Message sent when user is being ratelimited for an inbox
            # {0}: the duration in seconds to wait before retrying
            content = _("You are creating tickets too quickly! Please wait {0:.0f}s.")
            content = await translate(content, interaction)
            content = content.format(retry_after)
            return await interaction.response.send_message(content, ephemeral=True)

        # Message sent when creating a ticket
        content = await translate(_("Creating ticket..."), interaction)
        await interaction.response.send_message(content, ephemeral=True)

        async with self.bot.acquire() as conn:
            query = DatabaseClient(conn)
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

        # Audit log reason for a user creating a ticket
        # {0}: the user's name
        reason = _("Ticket created by {0}")
        reason = await translate(reason, interaction, locale=guild.preferred_locale)
        reason = reason.format(interaction.user.name)

        try:
            ticket = await interaction.channel.create_thread(
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
            content = _(
                # Message sent when creating a ticket failed due to insufficient permissions
                "I am missing the permissions needed to create a ticket here. "
                "Please notify a server admin!"
            )
            content = await translate(content, interaction)
            return await interaction.edit_original_response(content=content)
        except Exception:
            # Message sent when creating a ticket failed unexpectedly
            content = _("An unexpected error occurred while creating the ticket.")
            content = await translate(content, interaction)
            await interaction.edit_original_response(content=content)
            raise
        else:
            # Message sent after successfully creating a ticket
            # {0}: the ticket's link
            content = _("Your ticket is ready! {0}")
            content = await translate(content, interaction)
            content = content.format(ticket.jump_url)
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


async def get_and_filter_inbox_staff(
    query: DatabaseClient,
    guild: discord.Guild,
    inbox_id: int,
) -> list[str]:
    mentions = await query.get_inbox_staff(inbox_id)
    return await filter_and_update_inbox_staff(query, guild, inbox_id, mentions)


async def filter_and_update_inbox_staff(
    query: DatabaseClient,
    guild: discord.Guild,
    inbox_id: int,
    mentions: Sequence[str],
) -> list[str]:
    role_mentions = set(m for m in mentions if m.startswith("<@&"))
    current_roles = {role.mention for role in guild.roles}
    removed = role_mentions - current_roles

    for mention in removed:
        await query.remove_inbox_staff(inbox_id, mention)

    return [m for m in mentions if m not in removed]


class InboxStaffView(discord.ui.View):
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
            # Message sent when submitting no changes to inbox staff
            content = _("You have not made any changes!")
            content = await translate(content, interaction)
            return await interaction.response.send_message(content, ephemeral=True)

        async with self.bot.acquire() as conn:
            query = DatabaseClient(conn)
            for mention in added:
                await query.add_inbox_staff(self.inbox_id, mention)
            for mention in removed:
                await query.remove_inbox_staff(self.inbox_id, mention)

        self.staff = mentions
        await interaction.response.defer()


def mention_to_snowflake(mention: str) -> discord.Object:
    m = MENTION_PATTERN.fullmatch(mention)
    if m is None:
        raise ValueError(f"Invalid user/role mention: {mention!r}")

    if m[1] == "@":
        return discord.Object(int(m[2]), type=discord.User)
    elif m[1] == "@&":
        return discord.Object(int(m[2]), type=discord.Role)
    raise RuntimeError(f"Unsupported mention type {m[1]!r}")


def snowflake_to_mention(obj: discord.Member | discord.Role | discord.Object) -> str:
    if not isinstance(obj, discord.Object):
        return obj.mention
    elif obj.type is discord.abc.User:
        return f"<@{obj.id}>"
    elif issubclass(obj.type, discord.Role):
        return f"<@&{obj.id}>"
    raise ValueError(f"Unsupported object type {obj.type}")


class SetInboxStarterContentModal(discord.ui.Modal, title="Starter Message"):
    content = discord.ui.TextInput(
        label="Content",
        style=discord.TextStyle.long,
        max_length=2000,
        required=False,
    )

    def __init__(self, bot: Bot, inbox: discord.Message) -> None:
        super().__init__()
        self.bot = bot
        self.inbox = inbox

    async def localize(self, locale: discord.Locale) -> None:
        async def t(s: _) -> str:
            return await translate(s, self.bot, locale=locale)

        # Modal title for changing an inbox's starter message
        self.title = await t(_("Starter Message"))
        # Modal text input label for an inbox's starter message content
        self.content.label = await t(_("Content"))

    async def set_defaults(self, conn: asqlite.Connection) -> None:
        query = DatabaseClient(conn)
        starter_content = await query.get_inbox_starter_content(self.inbox.id)
        starter_content = starter_content or DEFAULT_STARTER_CONTENT
        self.content.default = starter_content

    async def on_submit(self, interaction: discord.Interaction):
        async with self.bot.acquire() as conn:
            query = DatabaseClient(conn)
            await query.set_inbox_starter_content(self.inbox.id, self.content.value)

        # Message sent when an inbox's starter message is successfully changed
        # {0}: the inbox's link
        content = _("{0} 's starting message has been set!")
        content = await translate(content, interaction)
        content = content.format(self.inbox.jump_url)
        await interaction.response.send_message(content, ephemeral=True)


class SetTicketDefaultsModal(discord.ui.Modal, title="New Tickets"):
    name = discord.ui.TextInput(label="Name", max_length=100, required=False)

    def __init__(self, bot: Bot, inbox: discord.Message) -> None:
        super().__init__()
        self.bot = bot
        self.inbox = inbox

    async def localize(self, locale: discord.Locale) -> None:
        async def t(s: _) -> str:
            return await translate(s, self.bot, locale=locale)

        # Modal title for changing an inbox's defaults for new tickets
        self.title = await t(_("New Tickets"))
        # Modal text input label for ticket names
        self.name.label = await t(_("Name"))

    async def set_defaults(self, conn: asqlite.Connection) -> None:
        query = DatabaseClient(conn)
        ticket_name = await query.get_inbox_default_ticket_name(self.inbox.id)
        ticket_name = ticket_name or DEFAULT_TICKET_NAME
        self.name.default = ticket_name

    async def on_submit(self, interaction: discord.Interaction):
        async with self.bot.acquire() as conn:
            query = DatabaseClient(conn)
            await query.set_inbox_default_ticket_name(self.inbox.id, self.name.value)

        # Message sent when an inbox's ticket defaults were successfully changed
        # {0}: the inbox's link
        content = _("{0} 's ticket defaults have been set!")
        content = await translate(content, interaction)
        content = content.format(self.inbox.jump_url)
        await interaction.response.send_message(content, ephemeral=True)


def looks_like_an_inbox(bot: Bot, message: discord.Message) -> bool:
    # Good enough as a heuristic
    assert bot.user is not None
    return message.author.id == bot.user.id and len(message.components) > 0


class InboxMessageParams(TypedDict):
    embeds: list[discord.Embed]
    files: list[discord.File]


@app_commands.default_permissions(manage_guild=True)
@app_commands.guild_only()
class Inbox(
    commands.GroupCog,
    # Command group name
    # (alternatively translated as "panel")
    group_name=_("inbox"),
    # Command group description ("inbox")
    group_description=_("Manage the server's ticket inboxes."),
):
    _inbox_ratelimits: dict[tuple[int, int], tuple[float, app_commands.Cooldown]]

    def __init__(self, bot: Bot):
        self.bot = bot

        self._global_inbox_view = self.create_inbox_view()
        self._inbox_views: dict[int, InboxView] = {}
        self._inbox_ratelimits = {}

        self.cleanup_loop.start()
        self.bot.add_view(self._global_inbox_view)

    def create_inbox_view(self) -> InboxView:
        return InboxView(self.bot, ratelimit_check=self.check_ratelimit)

    async def cog_unload(self) -> None:
        self._global_inbox_view.stop()
        for view in self._inbox_views.values():
            view.stop()

    async def check_ratelimit(
        self,
        inbox: discord.Message,
        member: discord.Member,
    ) -> float:
        assert isinstance(inbox.channel, discord.TextChannel)

        key = (inbox.id, member.id)
        per = max(60.0, inbox.channel.slowmode_delay)
        per_cooldown = self._inbox_ratelimits.get(key)

        # Allow cooldowns to reset when slowmode is changed
        if per_cooldown is None or per != per_cooldown[0]:
            per_cooldown = (per, app_commands.Cooldown(1, per))
            self._inbox_ratelimits[key] = per_cooldown

        per, cooldown = per_cooldown
        return cooldown.update_rate_limit(time.monotonic()) or 0

    def set_inbox_callback(
        self,
        interaction: discord.Interaction,
        callback: MessageCallback,
    ) -> None:
        async def wrapper(interaction: discord.Interaction, message: discord.Message):
            # As long as message callbacks are guild-specific,
            # this assert should always be true
            assert interaction.guild == original_interaction.guild

            await self.check_inbox_message(interaction, message)
            await callback(interaction, message)

        assert interaction.guild is not None
        original_interaction = interaction
        self.bot.set_message_callback(
            interaction.guild.id,
            interaction.user.id,
            wrapper,
        )

    async def check_inbox_message(
        self,
        interaction: discord.Interaction,
        message: discord.Message,
    ) -> None:
        assert isinstance(interaction.user, discord.Member)

        async with self.bot.acquire() as conn:
            row = await conn.fetchone("SELECT 1 FROM inbox WHERE id = ?", message.id)

        if row is None:
            if looks_like_an_inbox(self.bot, message):
                content = _(
                    # Message sent when selecting a non-inbox message
                    # that looks like the message used to be an inbox
                    # {0}: the message's link
                    "Sorry, {0} is no longer recognized as an inbox "
                    "and must be re-created."
                )
            else:
                content = _(
                    # Message sent when selecting a non-inbox message
                    # {0}: the message's link
                    "Sorry, {0} is not an inbox. The message you select should have "
                    "a **Create Ticket** button under it."
                )

            content = await translate(content, interaction)
            content = content.format(message.jump_url)
            raise AppCommandResponse(content)

    @app_commands.command(
        # Subcommand name ("inbox")
        name=_("create"),
        # Subcommand description ("inbox create")
        description=_("Create a new inbox."),
    )
    @app_commands.rename(
        # Subcommand parameter name ("inbox create")
        channel=_("channel"),
    )
    @app_commands.describe(
        # Subcommand parameter description ("inbox create <channel>")
        channel=_("The channel to post the inbox."),
    )
    async def create(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ):
        assert interaction.guild is not None

        # TODO: limit number of inboxes per guild

        bot_permissions = channel.permissions_for(interaction.guild.me)
        required = discord.Permissions(
            view_channel=True,
            send_messages=True,
            create_private_threads=True,
            send_messages_in_threads=True,
        )
        missing = bot_permissions & required ^ required
        if missing:
            missing = ", ".join(f"`{name}`" for name, value in missing if value)
            # Message sent when attempting to create an inbox with insufficient permissions
            # {0}: the channel's mention
            # {1}: a list of permissions that are missing
            content = _("I need the following permissions in {0}: {1}")
            content = await translate(content, interaction)
            content = content.format(channel.mention, missing)
            return await interaction.response.send_message(content, ephemeral=True)

        content = _(
            # Message sent when the user is creating a new inbox in a channel,
            # and the inbox needs a message to be included
            # {0}: the channel's mention
            "The {0} channel has been set as the destination for your new inbox. "
            "You must now select the message you want your inbox to have. "
            "To do this, right click or long tap a message, then open Apps "
            "and pick the *Select this message* command."
        )
        content = await translate(content, interaction)
        content = content.format(channel.mention)
        await interaction.response.send_message(content, ephemeral=True)
        self.bot.set_message_callback(
            interaction.guild.id,
            interaction.user.id,
            functools.partial(self.create_inbox, channel=channel),
        )

    async def create_inbox(
        self,
        interaction: discord.Interaction,
        message: discord.Message,
        channel: discord.TextChannel,
    ):
        assert interaction.guild is not None

        kwargs = await self.create_inbox_message(
            interaction,
            message,
            embed_url=channel.jump_url,
        )
        if kwargs is None:
            return

        view = self.create_inbox_view()
        await view.localize(interaction.guild.preferred_locale)

        message = await channel.send(view=view, **kwargs)
        assert message.guild is not None

        self._inbox_views[message.id] = view

        async with self.bot.acquire() as conn:
            query = DatabaseClient(conn)
            await query.add_inbox(
                message.id,
                message.channel.id,
                guild_id=message.guild.id,
            )

            starter_content = await translate(
                # The default starter message content for new tickets
                _("$author Thank you for creating a ticket!\n$staff"),
                interaction,
                locale=interaction.guild.preferred_locale,
            )
            await query.set_inbox_starter_content(message.id, starter_content)

            for staff in self.get_default_inbox_staff(channel):
                mention = snowflake_to_mention(staff)
                await query.add_inbox_staff(message.id, mention)

        # Message sent after a user creates an inbox
        # {0}: the inbox's link
        content = await translate(_("Your inbox has been created! {0}"), interaction)
        content = content.format(message.jump_url)
        await interaction.followup.send(content, ephemeral=True)

    async def create_inbox_message(
        self,
        interaction: discord.Interaction,
        message: discord.Message,
        *,
        embed_url: str | None = None,
    ) -> InboxMessageParams | None:
        embeds = [discord.Embed()]
        files: list[discord.File] = []

        if message.content != "":
            embeds[0].description = message.content

        max_attachment_size = self.bot.config.bot.inbox.max_attachment_size
        if sum(a.size for a in message.attachments) > max_attachment_size:
            content = _(
                # Message sent when attempting to create an inbox with too large attachments
                # {0}: the maximum cumulative filesize
                "The message's attachments are too large! "
                "The total size must be under {0}."
            )
            content = await translate(content, interaction)
            content = content.format(humanize.naturalsize(max_attachment_size))
            await interaction.response.send_message(content, ephemeral=True)
            return

        embeds_copied = False
        if len(embeds[0]) == 0 and len(message.embeds) > 0:
            embeds.clear()
            embeds.extend(embed.copy() for embed in message.embeds)
            embeds_copied = True

        await interaction.response.defer(ephemeral=True)

        url = embed_url or message.channel.jump_url
        for attachment in message.attachments:
            f = await attachment.to_file()
            files.append(f)
            image_url = f"attachment://{f.filename}"

            if embeds_copied:
                pass
            elif embeds[0].url is None:
                embeds[0].url = url
                embeds[0].set_image(url=image_url)
            else:
                embeds.append(discord.Embed(url=url).set_image(url=image_url))

        return {"embeds": embeds, "files": files}

    def get_default_inbox_staff(
        self,
        channel: discord.TextChannel,
    ) -> list[discord.Member | discord.Role | discord.Object]:
        assert self.bot.user is not None
        return [
            target
            for target, overwrite in channel.overwrites.items()
            if overwrite.manage_threads and target.id != self.bot.user.id
        ]

    @app_commands.command(
        # Subcommand name ("inbox")
        name=_("message"),
        # Subcommand description ("inbox message")
        description=_("Edit the message for an inbox."),
    )
    async def message(self, interaction: discord.Interaction):
        content = _(
            # Message sent when a user is editing an inbox's message,
            # and an inbox needs to be selected
            "You must now select the inbox you want to edit. "
            "To do this, right click or long tap a message, then open Apps "
            "and pick the *Select this message* command."
        )
        content = await translate(content, interaction)
        await interaction.response.send_message(content, ephemeral=True)
        self.set_inbox_callback(interaction, self.select_message_to_edit_inbox)

    async def select_message_to_edit_inbox(
        self,
        interaction: discord.Interaction,
        inbox: discord.Message,
    ):
        assert interaction.guild is not None
        guild_id = interaction.guild.id
        user_id = interaction.user.id

        # Message sent when a user is editing an inbox's message,
        # and a second message needs to be selected to copy its contents
        # {0}: the inbox's link
        content = _("{0} will be edited. Please select the message you want to copy.")
        content = await translate(content, interaction)
        content = content.format(inbox.jump_url)
        await interaction.response.send_message(content, ephemeral=True)
        callback = functools.partial(self.edit_inbox_message, inbox=inbox)
        self.bot.set_message_callback(guild_id, user_id, callback)

    async def edit_inbox_message(
        self,
        interaction: discord.Interaction,
        message: discord.Message,
        inbox: discord.Message,
    ):
        assert interaction.guild is not None

        if message == inbox:
            content = _(
                # Message sent when a user tries to edit an inbox message with itself
                "The inbox message cannot be edited with itself. "
                "Please select another message you want to copy."
            )
            raise AppCommandResponse(content)

        kwargs = await self.create_inbox_message(
            interaction,
            message,
            embed_url=inbox.channel.jump_url,
        )
        if kwargs is None:
            return

        kwargs = cast(dict[str, Any], kwargs)
        kwargs["attachments"] = kwargs.pop("files")

        # In case the guild locale changed, re-edit the view as well
        view = self.create_inbox_view()
        await view.localize(interaction.guild.preferred_locale)
        await inbox.edit(view=view, **kwargs)
        self._inbox_views[inbox.id] = view

        # Message sent after a user edits an inbox's message
        # {0}: the inbox's link
        content = await translate(_("{0} has been updated!"), interaction)
        content = content.format(inbox.jump_url)
        await interaction.followup.send(content, ephemeral=True)

    @app_commands.command(
        # Subcommand name ("inbox")
        name=_("staff"),
        # Subcommand description ("inbox staff")
        description=_("Manage staff for an inbox."),
    )
    async def staff(self, interaction: discord.Interaction):
        content = _(
            # Message sent when a user is managing staff for an inbox,
            # and an inbox needs to be selected
            "You must now select the inbox you want to manage staff for. "
            "To do this, right click or long tap a message, then open Apps "
            "and pick the *Select this message* command."
        )
        content = await translate(content, interaction)
        await interaction.response.send_message(content, ephemeral=True)
        self.set_inbox_callback(interaction, self.manage_inbox_staff)

    async def manage_inbox_staff(
        self,
        interaction: discord.Interaction,
        inbox: discord.Message,
    ):
        assert interaction.guild is not None
        async with self.bot.acquire() as conn:
            query = DatabaseClient(conn)
            staff = await get_and_filter_inbox_staff(query, interaction.guild, inbox.id)

        # Message sent above select menus when presenting an inbox's staff
        # {0}: the inbox's link
        content = _("Staff for {0} :")
        content = await translate(content, interaction)
        content = content.format(inbox.jump_url)
        view = InboxStaffView(self.bot, inbox.id, set(staff))

        return await interaction.response.send_message(
            content,
            ephemeral=True,
            view=view,
        )

    new_tickets = app_commands.Group(
        # Subcommand group name ("inbox")
        name=_("new-tickets"),
        # Subcommand group description ("inbox new-tickets")
        description=_("Manage new tickets created by an inbox."),
    )

    @new_tickets.command(
        # Subcommand name ("inbox new-tickets")
        name=_("starter"),
        # Subcommand description ("inbox new-tickets starter")
        description=_("Set the starting message for new tickets."),
    )
    async def new_tickets_starter(self, interaction: discord.Interaction):
        content = _(
            # Message sent when a user is changing the starter message for new tickets,
            # and an inbox needs to be selected
            "You must now select the inbox you want to edit. "
            "To do this, right click or long tap a message, then open Apps "
            "and pick the *Select this message* command."
        )
        content = await translate(content, interaction)
        await interaction.response.send_message(content, ephemeral=True)
        self.set_inbox_callback(interaction, self.edit_new_tickets_starter)

    async def edit_new_tickets_starter(
        self,
        interaction: discord.Interaction,
        inbox: discord.Message,
    ):
        modal = SetInboxStarterContentModal(self.bot, inbox)
        async with self.bot.acquire() as conn:
            await modal.set_defaults(conn)
        await modal.localize(interaction.locale)
        await interaction.response.send_modal(modal)

    @new_tickets.command(
        # Subcommand name ("inbox new-tickets")
        name=_("name"),
        # Subcommand description ("inbox new-tickets name")
        description=_("Set the name for new tickets."),
    )
    async def new_tickets_name(self, interaction: discord.Interaction):
        content = _(
            # Message sent when a user is changing the name for new tickets,
            # and an inbox needs to be selected
            "You must now select the inbox you want to edit. "
            "To do this, right click or long tap a message, then open Apps "
            "and pick the *Select this message* command."
        )
        content = await translate(content, interaction)
        await interaction.response.send_message(content, ephemeral=True)
        self.set_inbox_callback(interaction, self.edit_new_tickets_name)

    async def edit_new_tickets_name(
        self,
        interaction: discord.Interaction,
        inbox: discord.Message,
    ):
        modal = SetTicketDefaultsModal(self.bot, inbox)
        async with self.bot.acquire() as conn:
            await modal.set_defaults(conn)
        await modal.localize(interaction.locale)
        await interaction.response.send_modal(modal)

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

        # Message sent when a user leaves their ticket
        # {0}: The ticket owner's mention
        content = _("Archiving ticket as the owner ({0}) has left the thread.")
        content = await translate(content, self.bot, locale=guild.preferred_locale)
        content = content.format(f"<@{owner_id}>")
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

            # Message sent when a user leaves a server with open tickets
            # {0}: The ticket owner's mention
            content = _("Archiving ticket as the owner ({0}) has left the server.")
            content = await translate(content, self.bot, locale=guild.preferred_locale)
            content = content.format(payload.user.mention)
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

        # Message sent when locking a thread after being archived
        content = _("This archived ticket will be locked to moderators only.")
        content = await translate(content, self.bot, locale=guild.preferred_locale)

        params = discord.http.handle_message_parameters(content)
        await self.bot.http.send_message(thread_id, params=params)
        await self.bot.http.edit_channel(thread_id, archived=True, locked=True)

    @tasks.loop(minutes=30)
    async def cleanup_loop(self) -> None:
        now = time.monotonic()

        to_remove: list[tuple[int, int]] = []
        for key, (_, cooldown) in self._inbox_ratelimits.items():
            if now > cooldown._last + cooldown.per:  # unfortunate reliance on internals
                to_remove.append(key)

        for key in to_remove:
            del self._inbox_ratelimits[key]


async def setup(bot: Bot):
    await bot.add_cog(Inbox(bot))
