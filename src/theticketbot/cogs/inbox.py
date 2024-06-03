import string
import time
from typing import Iterable, Protocol

import asqlite
import discord
from discord import app_commands
from discord.app_commands import locale_str as _
from discord.ext import commands, tasks
import humanize

from theticketbot.bot import Bot
from theticketbot.database import DatabaseClient
from theticketbot.translator import translate

DEFAULT_STARTER_CONTENT = "$author $staff"


class InboxRatelimit(Protocol):
    async def __call__(self, inbox_id: int, user_id: int, /) -> bool: ...


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
        assert interaction.guild is not None
        assert interaction.message is not None

        guild = interaction.guild
        message = interaction.message

        async with self.bot.acquire() as conn:
            tickets = await self.get_active_user_tickets(
                guild.threads,
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

        if not await self.ratelimit_check(message.id, interaction.user.id):
            # Message sent when user is being ratelimited for an inbox
            content = _("You are creating tickets too quickly!")
            content = await translate(content, interaction)
            return await interaction.response.send_message(content, ephemeral=True)

        # Message sent when creating a ticket
        content = await translate(_("Creating ticket..."), interaction)
        await interaction.response.send_message(content, ephemeral=True)

        name = "{} {}".format(
            interaction.created_at.strftime("%Y-%m-%d"),
            interaction.user.display_name,
        )

        # Audit log reason for a user creating a ticket
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
        c = await conn.execute(
            "SELECT id FROM ticket WHERE inbox_id = ? AND owner_id = ?",
            inbox_id,
            owner_id,
        )
        ticket_ids: set[int] = {row[0] for row in await c.fetchall()}
        return [t for t in threads if t.id in ticket_ids]

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
        content = _("{0}'s starting content has been set!")
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
    MAX_ATTACHMENT_SIZE = 10**6 * 5

    def __init__(self, bot: Bot):
        self.bot = bot

        self._global_inbox_view = self.create_inbox_view()
        self._inbox_views: dict[int, InboxView] = {}
        self._inbox_ratelimits: dict[tuple[int, int], app_commands.Cooldown] = {}

        self.cleanup_loop.start()
        self.bot.add_view(self._global_inbox_view)

    def create_inbox_view(self) -> InboxView:
        return InboxView(self.bot, ratelimit_check=self.check_ratelimit)

    async def cog_unload(self) -> None:
        self._global_inbox_view.stop()
        for view in self._inbox_views.values():
            view.stop()

    async def check_ratelimit(self, inbox_id: int, user_id: int) -> bool:
        key = (inbox_id, user_id)
        cooldown = self._inbox_ratelimits.setdefault(key, app_commands.Cooldown(1, 60))
        return cooldown.update_rate_limit(time.monotonic()) is None

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

        if sum(a.size for a in message.attachments) > self.MAX_ATTACHMENT_SIZE:
            # Message sent when attempting to create an inbox with too large attachments
            # {0}: The maximum filesize allowed
            content = _(
                "The message's attachments are too large! "
                "The total size must be under {0}."
            )
            content = await translate(content, interaction)
            content = content.format(humanize.naturalsize(self.MAX_ATTACHMENT_SIZE))
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
                _("$author Thank you for creating a ticket!\nStaff: $staff"),
                interaction,
                locale=interaction.guild.preferred_locale,
            )
            await query.set_inbox_starter_content(message.id, starter_content)

        content = await translate(_("Your inbox has been created! {0}"), interaction)
        content = content.format(message.jump_url)
        await interaction.followup.send(content, ephemeral=True)

    staff = app_commands.Group(
        # Subcommand group name ("ticket")
        name=_("staff"),
        # Subcommand group description ("ticket staff")
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
        messages = self.bot.get_selected_messages(interaction.user.id)
        if len(messages) < 1:
            # Message sent when attempting to add an inbox staff without a message
            content = _(
                "Before you can use this command, you must select an inbox "
                "message. To do this, right click or long tap a message, "
                "then open Apps and pick the *Select this message* command."
            )
            content = await translate(content, interaction)
            return await interaction.response.send_message(content, ephemeral=True)

        inbox = messages[-1]

        async with self.bot.acquire() as conn:
            await DatabaseClient(conn).add_inbox_staff(inbox.id, staff.mention)

        # Message sent when adding staff to an inbox
        # {0}: the staff's mention
        # {1}: the inbox's link
        content = await translate(_("{0} has been added to inbox {1}!"), interaction)
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
        messages = self.bot.get_selected_messages(interaction.user.id)
        if len(messages) < 1:
            # Message sent when attempting to remove an inbox staff without a message
            content = _(
                "Before you can use this command, you must select an inbox "
                "message. To do this, right click or long tap a message, "
                "then open Apps and pick the *Select this message* command."
            )
            content = await translate(content, interaction)
            return await interaction.response.send_message(content, ephemeral=True)

        inbox = messages[-1]

        async with self.bot.acquire() as conn:
            await DatabaseClient(conn).remove_inbox_staff(inbox.id, staff.mention)

        # Message sent when removing staff from an inbox
        # {0}: the staff's mention
        # {1}: the inbox's link
        content = await translate(
            _("{0} has been removed from inbox {1}!"), interaction
        )
        content = content.format(staff.mention, inbox.jump_url)
        await interaction.response.send_message(content, ephemeral=True)

    @staff.command(
        # Subcommand name ("inbox staff")
        name=_("list"),
        # Subcommand description ("inbox staff list")
        description=_("List all staff members for an inbox."),
    )
    async def staff_list(self, interaction: discord.Interaction):
        messages = self.bot.get_selected_messages(interaction.user.id)
        if len(messages) < 1:
            # Message sent when attempting to list inbox staff without a message
            content = _(
                "Before you can use this command, you must select an inbox "
                "message. To do this, right click or long tap a message, "
                "then open Apps and pick the *Select this message* command."
            )
            content = await translate(content, interaction)
            return await interaction.response.send_message(content, ephemeral=True)

        inbox = messages[-1]

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

    starter = app_commands.Group(
        # Subcommand group name ("ticket")
        name=_("starter"),
        # Subcommand group description ("ticket starter")
        description=_("Manage the starting message for an inbox's tickets."),
    )

    @starter.command(
        # Subcommand name ("inbox starter")
        name=_("set"),
        # Subcommand description ("inbox starter set")
        description=_("Set the starting content for an inbox's tickets."),
    )
    async def starter_set(self, interaction: discord.Interaction):
        messages = self.bot.get_selected_messages(interaction.user.id)
        if len(messages) < 1:
            # Message sent when attempting to set inbox starter content without a message
            content = _(
                "Before you can use this command, you must select an inbox "
                "message. To do this, right click or long tap a message, "
                "then open Apps and pick the *Select this message* command."
            )
            content = await translate(content, interaction)
            return await interaction.response.send_message(content, ephemeral=True)

        inbox = messages[-1]

        modal = SetInboxStarterContentModal(self.bot, inbox)
        async with self.bot.acquire() as conn:
            await modal.set_defaults(conn)
        await modal.localize(interaction.locale)
        await interaction.response.send_modal(modal)

    @starter.command(
        # Subcommand name ("inbox starter")
        name=_("get"),
        # Subcommand description ("inbox starter get")
        description=_("Get the starting content for an inbox's tickets."),
    )
    async def starter_get(self, interaction: discord.Interaction):
        messages = self.bot.get_selected_messages(interaction.user.id)
        if len(messages) < 1:
            # Message sent when attempting to get inbox starter content without a message
            content = _(
                "Before you can use this command, you must select an inbox "
                "message. To do this, right click or long tap a message, "
                "then open Apps and pick the *Select this message* command."
            )
            content = await translate(content, interaction)
            return await interaction.response.send_message(content, ephemeral=True)

        inbox = messages[-1]

        async with self.bot.acquire() as conn:
            query = DatabaseClient(conn)
            starter_content = await query.get_inbox_starter_content(inbox.id)
            starter_content = starter_content or DEFAULT_STARTER_CONTENT

        await interaction.response.send_message(starter_content, ephemeral=True)

    @tasks.loop(minutes=30)
    async def cleanup_loop(self) -> None:
        now = time.monotonic()

        to_remove: list[tuple[int, int]] = []
        for key, cooldown in self._inbox_ratelimits.items():
            if now > cooldown._last + cooldown.per:  # unfortunate reliance on internals
                to_remove.append(key)

        for key in to_remove:
            del self._inbox_ratelimits[key]


async def setup(bot: Bot):
    await bot.add_cog(Inbox(bot))
