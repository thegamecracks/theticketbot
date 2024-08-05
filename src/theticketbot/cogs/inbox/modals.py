import asqlite
import discord
from discord.app_commands import locale_str

from theticketbot.bot import Bot
from theticketbot.database import DatabaseClient
from theticketbot.translator import locale_str as _, translate

from .constants import DEFAULT_STARTER_CONTENT, DEFAULT_TICKET_NAME


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
        async def t(s: locale_str) -> str:
            return await translate(s, self.bot, locale=locale)

        self.title = await t(_("modal-starter"))
        self.content.label = await t(_("modal-starter.content"))

    async def set_defaults(self, conn: asqlite.Connection) -> None:
        query = DatabaseClient(conn)
        starter_content = await query.get_inbox_starter_content(self.inbox.id)
        starter_content = starter_content or DEFAULT_STARTER_CONTENT
        self.content.default = starter_content

    async def on_submit(self, interaction: discord.Interaction):
        async with self.bot.acquire() as conn:
            query = DatabaseClient(conn)
            await query.set_inbox_starter_content(self.inbox.id, self.content.value)

        content = await translate(
            _("modal-starter-finished"),
            interaction,
            data={"inbox": self.inbox.jump_url},
        )
        await interaction.response.send_message(content, ephemeral=True)


class SetTicketDefaultsModal(discord.ui.Modal, title="New Tickets"):
    name = discord.ui.TextInput(label="Name", max_length=100, required=False)

    def __init__(self, bot: Bot, inbox: discord.Message) -> None:
        super().__init__()
        self.bot = bot
        self.inbox = inbox

    async def localize(self, locale: discord.Locale) -> None:
        async def t(s: locale_str) -> str:
            return await translate(s, self.bot, locale=locale)

        self.title = await t(_("modal-new-tickets"))
        self.name.label = await t(_("modal-new-tickets.name"))

    async def set_defaults(self, conn: asqlite.Connection) -> None:
        query = DatabaseClient(conn)
        ticket_name = await query.get_inbox_default_ticket_name(self.inbox.id)
        ticket_name = ticket_name or DEFAULT_TICKET_NAME
        self.name.default = ticket_name

    async def on_submit(self, interaction: discord.Interaction):
        async with self.bot.acquire() as conn:
            query = DatabaseClient(conn)
            await query.set_inbox_default_ticket_name(self.inbox.id, self.name.value)

        content = await translate(
            _("inbox-new-tickets-finished"),
            interaction,
            data={"inbox": self.inbox.jump_url},
        )
        await interaction.response.send_message(content, ephemeral=True)
