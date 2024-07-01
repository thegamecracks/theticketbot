from typing import Sequence

import discord

from theticketbot.database import DatabaseClient


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
