from . import config
from . import common
from . import discord
from . import analytics

import logging

logger = logging.getLogger(__name__)
logger.info("loading...")

#new member to the server. message = discord.Message
@discord.bot.event
async def on_message_delete(message): 
    msgProcessStart = analytics.getEventTime()
    if common.isDiscordMainServer(message.server.id) is not True:
        return

    pass