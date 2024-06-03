import logging
import sqlite3
import string
import time
from typing import Awaitable, Callable, Iterable

import asqlite
import discord
import humanize
from discord import app_commands
from discord.app_commands import locale_str as _
from discord.ext import commands, tasks

from theticketbot.bot import Bot
from theticketbot.database import DatabaseClient
from theticketbot.translator import translate

DEFAULT_STARTER_CONTENT = "$author $staff"

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
                # Message sent when a user tries using a deleted inbox
                content = _(
                    "Sorry, this inbox is no longer recognized and must be "
                    "re-created. Please notify a server admin!"
                )
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
            # Message sent when trying to create too many tickets
            # {0}: the ticket's link
            content = _(
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

        name = "{} {}".format(
            interaction.created_at.strftime("%Y-%m-%d"),
            interaction.user.display_name,
        )

        # Audit log reason for a user creating a ticket
        # {0}: the user's name
        reason = _("Ticket created by {0}")
        reason = await translate(reason, interaction, locale=guild.preferred_locale)
        reason = reason.format(interaction.user.name)

        try:
            ticket = await interaction.channel.create_thread(
                name=name,
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
                mentions = await query.get_inbox_staff(message.id)
                mentions = ", ".join(mentions)

                starter_content = await query.get_inbox_starter_content(message.id)
                starter_content = starter_content or DEFAULT_STARTER_CONTENT

            content = string.Template(starter_content).safe_substitute(
                author=interaction.user.mention,
                staff=mentions,
            )
            await ticket.send(content[:2000])
        except discord.Forbidden:
            # Message sent when creating a ticket failed due to insufficient permissions
            content = _(
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


class SetInboxStarterContentModal(discord.ui.Modal, title="Set Inbox Starter"):
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

        # Modal title for setting inbox starter
        self.title = await t(_("Set Inbox Starter"))
        # Modal text input label for inbox starter content
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

        # Message sent when setting inbox starter content
        # {0}: the inbox's link
        content = _("{0} 's starting content has been set!")
        content = await translate(content, interaction)
        content = content.format(self.inbox.jump_url)
        await interaction.response.send_message(content, ephemeral=True)


@app_commands.default_permissions(manage_guild=True)
class Inbox(
    commands.GroupCog,
    # Command group name
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

    async def maybe_get_inbox_message(
        self,
        interaction: discord.Interaction,
    ) -> discord.Message | None:
        messages = self.bot.get_selected_messages(interaction.user.id)
        if len(messages) < 1:
            # Message sent when using a command without selecting an inbox message
            content = _(
                "Before you can use this command, you must select an inbox "
                "message. To do this, right click or long tap a message, "
                "then open Apps and pick the *Select this message* command."
            )
            content = await translate(content, interaction)
            return await interaction.response.send_message(content, ephemeral=True)

        inbox = messages[-1]
        if await self.check_inbox_message(interaction, inbox):
            return inbox

    async def check_inbox_message(
        self,
        interaction: discord.Interaction,
        message: discord.Message,
    ) -> bool:
        async with self.bot.acquire() as conn:
            row = await conn.fetchone("SELECT 1 FROM inbox WHERE id = ?", message.id)

        if row is not None:
            return True

        # Message sent when message is not an inbox
        # {0}: the inbox's link
        content = await translate(_("{0} is not an inbox."), interaction)
        content = content.format(message.jump_url)
        await interaction.response.send_message(content, ephemeral=True)
        return False

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

        messages = self.bot.get_selected_messages(interaction.user.id)
        if len(messages) < 1:
            # Message sent when attempting to create an inbox without a message
            content = _(
                "Before you can use this command, you must select a message "
                "to be sent with the inbox. To do this, right click or long tap "
                "a message, then open Apps and pick the *Select this message* command."
            )
            content = await translate(content, interaction)
            return await interaction.response.send_message(content, ephemeral=True)

        message = messages[-1]
        embeds = [discord.Embed()]
        files: list[discord.File] = []

        if message.content != "":
            embeds[0].description = message.content

        max_attachment_size = self.bot.config.bot.inbox.max_attachment_size
        if sum(a.size for a in message.attachments) > max_attachment_size:
            # Message sent when attempting to create an inbox with too large attachments
            # {0}: The maximum filesize allowed
            content = _(
                "The message's attachments are too large! "
                "The total size must be under {0}."
            )
            content = await translate(content, interaction)
            content = content.format(humanize.naturalsize(max_attachment_size))
            return await interaction.response.send_message(content, ephemeral=True)

        embeds_copied = False
        if len(embeds[0]) == 0 and len(message.embeds) > 0:
            embeds.clear()
            embeds.extend(embed.copy() for embed in message.embeds)
            embeds_copied = True

        await interaction.response.defer(ephemeral=True)

        url = channel.jump_url
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

        view = self.create_inbox_view()
        await view.localize(interaction.guild.preferred_locale)

        message = await channel.send(embeds=embeds, files=files, view=view)
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
                # The default starter content for new tickets
                _("$author Thank you for creating a ticket!\n$staff"),
                interaction,
                locale=interaction.guild.preferred_locale,
            )
            await query.set_inbox_starter_content(message.id, starter_content)

        # Message sent after the user creates an inbox
        # {0}: the inbox's link
        content = await translate(_("Your inbox has been created! {0}"), interaction)
        content = content.format(message.jump_url)
        await interaction.followup.send(content, ephemeral=True)

    staff = app_commands.Group(
        # Subcommand group name ("inbox")
        name=_("staff"),
        # Subcommand group description ("inbox staff")
        description=_("Manage staff for an inbox."),
    )

    @staff.command(
        # Subcommand name ("inbox staff")
        name=_("add"),
        # Subcommand description ("inbox staff add")
        description=_("Add a staff member or role for an inbox."),
    )
    @app_commands.rename(
        # Subcommand parameter name ("inbox staff add")
        staff=_("staff"),
    )
    @app_commands.describe(
        # Subcommand parameter description ("inbox staff add <staff>")
        staff=_("The staff member or role to add."),
    )
    async def staff_add(
        self,
        interaction: discord.Interaction,
        staff: discord.Member | discord.Role,
    ):
        if isinstance(staff, discord.Role) and staff == staff.guild.roles[0]:
            # Message sent when attempting to add everyone to inbox staff
            content = _("The everyone role cannot be added as staff.")
            content = await translate(content, interaction)
            return await interaction.response.send_message(content, ephemeral=True)

        inbox = await self.maybe_get_inbox_message(interaction)
        if inbox is None:
            return

        try:
            async with self.bot.acquire() as conn:
                await DatabaseClient(conn).add_inbox_staff(inbox.id, staff.mention)
        except sqlite3.IntegrityError:
            # Message sent when adding an already existing inbox staff
            # {0}: the staff's mention
            # {1}: the inbox's link
            content = _("{0} is already staff for inbox {1} .")
            content = await translate(content, interaction)
            content = content.format(staff.mention, inbox.jump_url)
            return await interaction.response.send_message(content, ephemeral=True)

        # Message sent when adding staff to an inbox
        # {0}: the staff's mention
        # {1}: the inbox's link
        content = await translate(_("{0} has been added to inbox {1} !"), interaction)
        content = content.format(staff.mention, inbox.jump_url)
        await interaction.response.send_message(content, ephemeral=True)

    @staff.command(
        # Subcommand name ("inbox staff")
        name=_("remove"),
        # Subcommand description ("inbox staff remove")
        description=_("Remove a staff member or role from an inbox."),
    )
    @app_commands.rename(
        # Subcommand parameter name ("inbox staff remove")
        staff=_("staff"),
    )
    @app_commands.describe(
        # Subcommand parameter description ("inbox staff remove <staff>")
        staff=_("The staff member or role to remove."),
    )
    async def staff_remove(
        self,
        interaction: discord.Interaction,
        staff: discord.Member | discord.Role,
    ):
        inbox = await self.maybe_get_inbox_message(interaction)
        if inbox is None:
            return

        async with self.bot.acquire() as conn:
            query = DatabaseClient(conn)
            success = await query.remove_inbox_staff(inbox.id, staff.mention)

        if success:
            # Message sent when removing staff from an inbox
            # {0}: the staff's mention
            # {1}: the inbox's link
            content = _("{0} has been removed from inbox {1} !")
        else:
            # Message sent when removing non-existent staff from an inbox
            # {0}: the staff's mention
            # {1}: the inbox's link
            content = _("{0} is not staff of inbox {1} .")

        content = await translate(content, interaction)
        content = content.format(staff.mention, inbox.jump_url)
        await interaction.response.send_message(content, ephemeral=True)

    @staff.command(
        # Subcommand name ("inbox staff")
        name=_("list"),
        # Subcommand description ("inbox staff list")
        description=_("List all staff members for an inbox."),
    )
    async def staff_list(self, interaction: discord.Interaction):
        inbox = await self.maybe_get_inbox_message(interaction)
        if inbox is None:
            return

        async with self.bot.acquire() as conn:
            mentions = await DatabaseClient(conn).get_inbox_staff(inbox.id)

        if len(mentions) > 0:
            mentions = ", ".join(mentions)
            await interaction.response.send_message(mentions, ephemeral=True)
        else:
            # Message sent when no staff can be listed for an inbox
            content = _("This inbox does not have any staff.")
            content = await translate(content, interaction)
            await interaction.response.send_message(content, ephemeral=True)

    new_tickets = app_commands.Group(
        # Subcommand group name ("inbox")
        name=_("new-tickets"),
        # Subcommand group description ("inbox new-tickets")
        description=_("Manage new tickets created by an inbox."),
    )

    @new_tickets.command(
        # Subcommand name ("inbox new-tickets")
        name=_("set-starter"),
        # Subcommand description ("inbox new-tickets set-starter")
        description=_("Set the starting message for new tickets."),
    )
    async def new_tickets_set_starter(self, interaction: discord.Interaction):
        inbox = await self.maybe_get_inbox_message(interaction)
        if inbox is None:
            return

        modal = SetInboxStarterContentModal(self.bot, inbox)
        async with self.bot.acquire() as conn:
            await modal.set_defaults(conn)
        await modal.localize(interaction.locale)
        await interaction.response.send_modal(modal)

    @commands.Cog.listener("on_raw_thread_member_remove")
    async def archive_abandoned_tickets(self, payload: discord.RawThreadMembersUpdate):
        # NOTE: event may not fire on already-archived tickets
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return log.warning("Ignoring unknown guild %d", payload.guild_id)

        thread = guild.get_thread(payload.thread_id)
        if thread is None:
            return log.warning("Ignoring unknown thread %d", payload.thread_id)

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

        # Message sent when owner leaves their ticket
        # {0}: The owner's mention
        content = _("Archiving ticket as the owner ({0}) has left the thread.")
        content = await translate(content, self.bot, locale=guild.preferred_locale)
        content = content.format(f"<@{owner_id}>")
        await thread.send(content, allowed_mentions=discord.AllowedMentions.none())
        await thread.edit(archived=True)

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
