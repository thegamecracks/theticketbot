import discord

from theticketbot.database import DatabaseClient


async def get_inbox_destination(
    query: DatabaseClient,
    guild: discord.Guild,
    inbox: discord.Message,
) -> discord.TextChannel:
    assert isinstance(inbox.channel, discord.TextChannel)

    channel_id = await query.get_inbox_destination(inbox.id)
    if channel_id is None:
        return inbox.channel

    channel = guild.get_channel(channel_id)
    if channel is None:
        return inbox.channel

    assert isinstance(channel, discord.TextChannel)
    return channel
