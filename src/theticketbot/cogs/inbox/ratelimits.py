import time

import discord
from discord import app_commands
from discord.ext import tasks


class InboxRatelimiter:
    _inbox_ratelimits: dict[tuple[int, int], app_commands.Cooldown]

    def __init__(self) -> None:
        self._inbox_ratelimits = {}

    async def __call__(
        self,
        inbox: discord.Message,
        member: discord.Member,
    ) -> float:
        assert isinstance(inbox.channel, discord.TextChannel)

        key = (inbox.id, member.id)
        per = max(60.0, inbox.channel.slowmode_delay)
        cooldown = self._inbox_ratelimits.get(key)

        # Allow cooldowns to reset when slowmode is changed
        if cooldown is None or cooldown.per != per:
            cooldown = app_commands.Cooldown(1, per)
            self._inbox_ratelimits[key] = cooldown

        return cooldown.update_rate_limit(time.monotonic()) or 0

    @tasks.loop(minutes=30)
    async def cleanup_loop(self) -> None:
        now = time.monotonic()

        to_remove: list[tuple[int, int]] = []
        for key, cooldown in self._inbox_ratelimits.items():
            if now > cooldown._last + cooldown.per:  # unfortunate reliance on internals
                to_remove.append(key)

        for key in to_remove:
            del self._inbox_ratelimits[key]
