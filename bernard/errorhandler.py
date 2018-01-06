print("%s loading..." % __name__) 

from . import config
from . import common
from . import discord

@discord.bot.event
async def on_error(event, *args, **kwargs):
	print(event)

	await xzbot.send_message(discord.objectFactory('283012703159844864'), "shits on fire yo")