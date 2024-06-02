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
        async with self.bot.acquire() as conn:
            return await self.handle_new_ticket(interaction, conn)

    # FIXME: this function is too big, can we do any better?
    async def handle_new_ticket(
        self,
        interaction: discord.Interaction,
        conn: asqlite.Connection,
    ):
        assert isinstance(interaction.channel, discord.TextChannel)
        assert interaction.guild is not None
        assert interaction.message is not None

        guild = interaction.guild
        message = interaction.message

        if not await self.ratelimit_check(message.id, interaction.user.id):
            # Message sent when user is being ratelimited for an inbox
            content = _("You are creating tickets too quickly!")
            content = await translate(content, interaction)
            return await interaction.response.send_message(content, ephemeral=True)

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

            query = DatabaseClient(conn)
            await query.add_ticket(ticket.id, message.id, interaction.user.id)

            mentions = await query.get_inbox_staff(message.id)
            mentions = ", ".join(mentions)

            starter_content = await query.get_inbox_starter_content(message.id)
            starter_content = starter_content or "$author $staff"

            content = string.Template(content).safe_substitute(
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
        except discord.HTTPException:
            # Message sent when creating a ticket failed unexpectedly
            content = _("An unexpected error occurred while creating the ticket.")
            content = await translate(content, interaction)
            await interaction.edit_original_response(content=content)
            raise
        else:
            # Message sent after successfully creating a ticket
            content = _("Your ticket is ready! {0}")
            content = await translate(content, interaction)
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
            "SELECT max_tickets_per_user FROM inbox WHERE inbox_id = ?",
            inbox_id,
        )
        assert row is not None
        return row[0]


class Inbox(
    commands.GroupCog,
    # Command group name
    group_name=_("inbox"),
):
    MAX_ATTACHMENT_SIZE = 10**6 * 5

    def __init__(self, bot: Bot):
        self.bot = bot
        self.view = self.create_inbox_view()
        self.bot.add_view(self.view)

        self._inbox_ratelimits: dict[tuple[int, int], app_commands.Cooldown] = {}
        self.cleanup_loop.start()

    def create_inbox_view(self) -> InboxView:
        return InboxView(self.bot, ratelimit_check=self.check_ratelimit)

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
    @app_commands.default_permissions(manage_guild=True)
    async def inbox(
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

        await interaction.response.defer(ephemeral=True)

        url = channel.jump_url
        for attachment in message.attachments:
            f = await attachment.to_file()
            files.append(f)
            image_url = f"attachment://{f.filename}"

            if embeds[0].url is None:
                embeds[0].url = url
                embeds[0].set_image(url=image_url)
            else:
                embeds.append(discord.Embed(url=url).set_image(url=image_url))

        if len(embeds[0]) == 0 and not embeds[0].url:
            embeds.clear()

        view = self.create_inbox_view()
        await view.localize(interaction.guild.preferred_locale)

        message = await channel.send(embeds=embeds, files=files, view=view)
        assert message.guild is not None

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
