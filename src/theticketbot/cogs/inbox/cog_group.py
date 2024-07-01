from __future__ import annotations

import functools
import logging
from typing import (
    TYPE_CHECKING,
    Any,
    TypedDict,
    cast,
)

import discord
import humanize
from discord import app_commands
from discord.app_commands import locale_str as _
from discord.ext import commands

from theticketbot.bot import Bot
from theticketbot.database import DatabaseClient
from theticketbot.errors import AppCommandResponse
from theticketbot.translator import translate

from .destination import get_inbox_destination
from .modals import SetInboxStarterContentModal, SetTicketDefaultsModal
from .ratelimits import InboxRatelimiter
from .staff import get_and_filter_inbox_staff
from .views import InboxStaffView, InboxView

if TYPE_CHECKING:
    from theticketbot.cogs.select import MessageCallback

log = logging.getLogger(__name__)


def snowflake_to_mention(obj: discord.Member | discord.Role | discord.Object) -> str:
    if not isinstance(obj, discord.Object):
        return obj.mention
    elif obj.type is discord.abc.User:
        return f"<@{obj.id}>"
    elif issubclass(obj.type, discord.Role):
        return f"<@&{obj.id}>"
    raise ValueError(f"Unsupported object type {obj.type}")


def looks_like_an_inbox(bot: Bot, message: discord.Message) -> bool:
    # Good enough as a heuristic
    assert bot.user is not None
    return message.author.id == bot.user.id and len(message.components) > 0


class InboxMessageParams(TypedDict):
    embeds: list[discord.Embed]
    files: list[discord.File]


@app_commands.default_permissions(manage_guild=True)
@app_commands.guild_only()
class InboxGroup(
    commands.GroupCog,
    # Command group name
    # (alternatively translated as "panel")
    group_name=_("inbox"),
    # Command group description ("inbox")
    group_description=_("Manage the server's ticket inboxes."),
):
    def __init__(self, bot: Bot):
        self.bot = bot

        self.inbox_ratelimiter = InboxRatelimiter()
        self.inbox_ratelimiter.cleanup_loop.start()

        self._global_inbox_view = self.create_inbox_view()
        self._inbox_views: dict[int, InboxView] = {}

        self.bot.add_view(self._global_inbox_view)

    def create_inbox_view(self) -> InboxView:
        return InboxView(self.bot, ratelimit_check=self.inbox_ratelimiter)

    async def cog_unload(self) -> None:
        self._global_inbox_view.stop()
        for view in self._inbox_views.values():
            view.stop()

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

    async def check_inbox_permissions(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> None:
        bot_permissions = channel.permissions_for(channel.guild.me)
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
        await self.check_inbox_permissions(interaction, channel)

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
        name=_("destination"),
        # Subcommand description ("inbox destination")
        description=_("Edit the destination channel for an inbox."),
    )
    @app_commands.rename(
        # Subcommand parameter name ("inbox destination")
        channel=_("channel"),
    )
    @app_commands.describe(
        # Subcommand parameter description ("inbox destination <channel>")
        channel=_("The channel to route new tickets."),
    )
    async def channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ):
        await self.check_inbox_permissions(interaction, channel)
        content = _(
            # Message sent when a user is editing an inbox's destination,
            # and an inbox needs to be selected
            "You must now select the inbox you want to edit. "
            "To do this, right click or long tap a message, then open Apps "
            "and pick the *Select this message* command."
        )
        content = await translate(content, interaction)
        await interaction.response.send_message(content, ephemeral=True)
        callback = functools.partial(self.edit_inbox_destination, destination=channel)
        self.set_inbox_callback(interaction, callback)

    async def edit_inbox_destination(
        self,
        interaction: discord.Interaction,
        inbox: discord.Message,
        destination: discord.TextChannel,
    ):
        assert inbox.guild is not None
        async with self.bot.acquire() as conn:
            query = DatabaseClient(conn)

            old = await get_inbox_destination(query, inbox.guild, inbox)
            if old.id == destination.id:
                # Message sent when an inbox's old and new destination are the same
                # {0}: the inbox's link
                # {1}: the destination's link
                content = _("{0} is already routing tickets to {1}!")
                content = await translate(content, interaction)
                content = content.format(inbox.jump_url, destination.jump_url)
                return await interaction.response.send_message(content, ephemeral=True)

            await query.set_inbox_destination(
                inbox.id,
                destination.id,
                guild_id=destination.guild.id,
            )

        # Message sent after a user edits an inbox's destination
        # {0}: the inbox's link
        # {1}: the old destination's link
        # {2}: the new destination's link
        content = _("{0} will now route tickets to {2} instead of {1}!")
        content = await translate(content, interaction)
        content = content.format(inbox.jump_url, old.jump_url, destination.jump_url)
        await interaction.response.send_message(content, ephemeral=True)

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
