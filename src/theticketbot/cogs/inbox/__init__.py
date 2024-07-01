from theticketbot.bot import Bot

from .cog_group import InboxGroup
from .cog_listeners import InboxListeners


async def setup(bot: Bot):
    await bot.add_cog(InboxGroup(bot))
    await bot.add_cog(InboxListeners(bot))
