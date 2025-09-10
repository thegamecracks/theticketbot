from __future__ import annotations

import functools
import logging
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    ParamSpec,
    TypeVar,
    TypedDict,
    cast,
)

import discord
import humanize
from discord import app_commands
from discord.ext import commands

from theticketbot.bot import Bot
from theticketbot.database import DatabaseClient
from theticketbot.errors import AppCommandResponse
from theticketbot.translator import locale_str as _, translate

from .destination import get_inbox_destination
from .modals import SetInboxStarterContentModal, SetTicketDefaultsModal
from .ratelimits import InboxRatelimiter
from .staff import get_and_filter_inbox_staff
from .views import InboxStaffView, InboxView

if TYPE_CHECKING:
    from theticketbot.cogs.select import MessageCallback

P = ParamSpec("P")
T = TypeVar("T")

REQUIRED_DESTINATION_PERMISSIONS = discord.Permissions(
    view_channel=True,
    create_private_threads=True,
    send_messages_in_threads=True,
)

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


def delete_interaction_and_call(
    callback: Callable[P, Awaitable[T]],
    interaction: discord.Interaction,
) -> Callable[P, Awaitable[T]]:
    @functools.wraps(callback)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        if not interaction.response.is_done():
            raise RuntimeError("No previous response was sent for this interaction")
        elif not interaction.is_expired():
            await interaction.delete_original_response()

        return await callback(*args, **kwargs)

    return wrapper


class InboxMessageParams(TypedDict):
    embeds: list[discord.Embed]
    files: list[discord.File]


@app_commands.default_permissions(manage_guild=True)
@app_commands.guild_only()
class InboxGroup(
    commands.GroupCog,
    group_name=_("command-inbox"),
    group_description=_("command-inbox.description"),
):
    def __init__(self, bot: Bot) -> None:
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
                content = _("select-unknown-inbox")
            else:
                content = _("select-invalid-inbox")

            data = {"message": message.jump_url}
            raise AppCommandResponse(content, data)

    async def check_bot_permissions(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        required: discord.Permissions,
    ) -> None:
        bot_permissions = channel.permissions_for(channel.guild.me)
        missing = bot_permissions & required ^ required
        if missing:
            missing = ", ".join(f"`{name}`" for name, value in missing if value)
            content = _("inbox-create-insufficient-permissions")
            data = {"channel": channel.mention, "permissions": missing}
            raise AppCommandResponse(content, data)

    @app_commands.command(
        name=_("command-inbox-create"),
        description=_("command-inbox-create.description"),
    )
    @app_commands.rename(
        channel=_("command-inbox-create.channel-name"),
        destination=_("command-inbox-create.destination-name"),
    )
    @app_commands.describe(
        channel=_("command-inbox-create.channel-description"),
        destination=_("command-inbox-create.destination-description"),
    )
    async def create(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        destination: discord.TextChannel | None,
    ):
        assert interaction.guild is not None
        destination = destination or channel

        # TODO: limit number of inboxes per guild

        channel_perms = discord.Permissions(view_channel=True, send_messages=True)
        destination_perms = REQUIRED_DESTINATION_PERMISSIONS

        if channel != destination:
            await self.check_bot_permissions(interaction, channel, channel_perms)
        else:
            destination_perms = destination_perms | channel_perms

        await self.check_bot_permissions(interaction, destination, destination_perms)

        content = await translate(
            _("inbox-create-with-message"),
            interaction,
            data={"channel": channel.mention, "destination": destination.mention},
        )
        await interaction.response.send_message(content, ephemeral=True)
        self.bot.set_message_callback(
            interaction.guild.id,
            interaction.user.id,
            functools.partial(
                delete_interaction_and_call(self.create_inbox, interaction),
                channel=channel,
                destination=destination,
            ),
        )

    async def create_inbox(
        self,
        interaction: discord.Interaction,
        message: discord.Message,
        channel: discord.TextChannel,
        destination: discord.TextChannel,
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
                _("ticket-starter-message-content"),
                interaction,
                locale=interaction.guild.preferred_locale,
            )
            await query.set_inbox_starter_content(message.id, starter_content)

            for staff in self.get_default_inbox_staff(destination):
                mention = snowflake_to_mention(staff)
                await query.add_inbox_staff(message.id, mention)

            if destination != channel:
                await query.set_inbox_destination(
                    message.id,
                    destination.id,
                    guild_id=message.guild.id,
                )

        content = await translate(
            _("inbox-create-finished"),
            interaction,
            data={"inbox": message.jump_url},
        )
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
            content = await translate(
                _("inbox-create-oversized-attachments"),
                interaction,
                data={"filesize": humanize.naturalsize(max_attachment_size)},
            )
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
        name=_("command-inbox-destination"),
        description=_("command-inbox-destination.description"),
    )
    @app_commands.rename(
        channel=_("command-inbox-destination.channel-name"),
    )
    @app_commands.describe(
        channel=_("command-inbox-destination.channel-description"),
    )
    async def channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ):
        await self.check_bot_permissions(
            interaction,
            channel,
            REQUIRED_DESTINATION_PERMISSIONS,
        )
        content = await translate(_("select-inbox-to-edit"), interaction)
        await interaction.response.send_message(content, ephemeral=True)
        self.set_inbox_callback(
            interaction,
            functools.partial(
                delete_interaction_and_call(self.edit_inbox_destination, interaction),
                destination=channel,
            ),
        )

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
                content = await translate(
                    _("inbox-destination-matches"),
                    interaction,
                    data={"inbox": inbox.jump_url, "destination": destination.jump_url},
                )
                return await interaction.response.send_message(content, ephemeral=True)

            await query.set_inbox_destination(
                inbox.id,
                destination.id,
                guild_id=destination.guild.id,
            )

        content = await translate(
            _("inbox-destination-changed"),
            interaction,
            data={
                "inbox": inbox.jump_url,
                "old": old.jump_url,
                "new": destination.jump_url,
            },
        )
        await interaction.response.send_message(content, ephemeral=True)

    @app_commands.command(
        name=_("command-inbox-message"),
        description=_("command-inbox-message.description"),
    )
    async def message(self, interaction: discord.Interaction):
        content = await translate(_("select-inbox-to-edit"), interaction)
        await interaction.response.send_message(content, ephemeral=True)
        self.set_inbox_callback(
            interaction,
            delete_interaction_and_call(self.select_message_to_edit_inbox, interaction),
        )

    async def select_message_to_edit_inbox(
        self,
        interaction: discord.Interaction,
        inbox: discord.Message,
    ):
        assert interaction.guild is not None
        guild_id = interaction.guild.id
        user_id = interaction.user.id

        content = await translate(
            _("inbox-message-select"),
            interaction,
            data={"inbox": inbox.jump_url},
        )
        await interaction.response.send_message(content, ephemeral=True)
        self.bot.set_message_callback(
            guild_id,
            user_id,
            functools.partial(
                delete_interaction_and_call(self.edit_inbox_message, interaction),
                inbox=inbox,
            ),
        )

    async def edit_inbox_message(
        self,
        interaction: discord.Interaction,
        message: discord.Message,
        inbox: discord.Message,
    ):
        assert interaction.guild is not None

        if message == inbox:
            raise AppCommandResponse(_("inbox-message-selected-self"))

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

        content = await translate(
            _("inbox-message-finished"),
            interaction,
            data={"inbox": inbox.jump_url},
        )
        await interaction.followup.send(content, ephemeral=True)

    @app_commands.command(
        name=_("command-inbox-staff"),
        description=_("command-inbox-staff.description"),
    )
    async def staff(self, interaction: discord.Interaction):
        content = await translate(_("select-inbox-to-edit-staff"), interaction)
        await interaction.response.send_message(content, ephemeral=True)
        self.set_inbox_callback(
            interaction,
            delete_interaction_and_call(self.manage_inbox_staff, interaction),
        )

    async def manage_inbox_staff(
        self,
        interaction: discord.Interaction,
        inbox: discord.Message,
    ):
        assert interaction.guild is not None
        async with self.bot.acquire() as conn:
            query = DatabaseClient(conn)
            staff = await get_and_filter_inbox_staff(query, interaction.guild, inbox.id)

        content = await translate(
            _("inbox-staff-message"),
            interaction,
            data={"inbox": inbox.jump_url},
        )
        view = InboxStaffView(self.bot, inbox.id, set(staff))

        await interaction.response.send_message(content, ephemeral=True, view=view)

    new_tickets = app_commands.Group(
        name=_("command-inbox-new-tickets"),
        description=_("command-inbox-new-tickets.description"),
    )

    @new_tickets.command(
        name=_("command-inbox-new-tickets-starter"),
        description=_("command-inbox-new-tickets-starter.description"),
    )
    async def new_tickets_starter(self, interaction: discord.Interaction):
        content = await translate(_("select-inbox-to-edit"), interaction)
        await interaction.response.send_message(content, ephemeral=True)
        self.set_inbox_callback(
            interaction,
            delete_interaction_and_call(self.edit_new_tickets_starter, interaction),
        )

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
        name=_("command-inbox-new-tickets-name"),
        description=_("command-inbox-new-tickets-name.description"),
    )
    async def new_tickets_name(self, interaction: discord.Interaction):
        content = await translate(_("select-inbox-to-edit"), interaction)
        await interaction.response.send_message(content, ephemeral=True)
        self.set_inbox_callback(
            interaction,
            delete_interaction_and_call(self.edit_new_tickets_name, interaction),
        )

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
