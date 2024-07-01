import asqlite
import discord
from discord.app_commands import locale_str as _

from theticketbot.bot import Bot
from theticketbot.database import DatabaseClient
from theticketbot.translator import translate

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
