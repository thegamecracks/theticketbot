from theticketbot.bot import Bot

from .cog import Inbox


async def setup(bot: Bot):
    await bot.add_cog(Inbox(bot))
