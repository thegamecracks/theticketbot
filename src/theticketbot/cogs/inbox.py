import discord
from discord import app_commands
from discord.app_commands import locale_str as _
from discord.ext import commands
import humanize

from theticketbot.bot import Bot
from theticketbot.translator import translate


class Inbox(
    commands.GroupCog,
    # Command group name
    group_name=_("inbox"),
):
    MAX_ATTACHMENT_SIZE = 10**6 * 5

    def __init__(self, bot: Bot):
        self.bot = bot

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
            content = await translate(content, self.bot)
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
            content = await translate(content, self.bot)
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
            content = await translate(content, self.bot)
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

        # TODO: add view for creating tickets
        # TODO: add inbox to database
        message = await channel.send(embeds=embeds, files=files)

        content = await translate(_("Your inbox has been created! {0}"), self.bot)
        content = content.format(message.jump_url)
        await interaction.followup.send(content, ephemeral=True)


async def setup(bot: Bot):
    await bot.add_cog(Inbox(bot))
