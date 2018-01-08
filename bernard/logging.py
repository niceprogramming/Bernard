print("%s loading..." % __name__) 

# Note: to the persons brave enough to read the source: this is logging for the bots code and errors, not logging chat messages. 
# This bot does not save user messages and never will.

from . import config
from . import common
from . import discord

import logging

logging.basicConfig(level=logging.INFO)

@discord.bot.event
async def on_error(event, *args, **kwargs):
	print(event)

	await discord.bot.send_message(discord.objectFactory('283012703159844864'), "{0} {1} {2}".format(event, args, kwargs))