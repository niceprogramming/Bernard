print("Importing... %s" % __name__)

from . import config
from . import common
from . import discord
from . import database
from . import auditing

import time

@discord.bot.event
async def on_message(message):
	msgProcessStart = time.time()
	#only reply to the guild set in config file
	if message.server.id != config.cfg['discord']['server']:
		return

	#package the message as a json object, add to a redis DB and set it to expire to anti-spam calculations
	database.rds.set(message.channel.id +":"+ message.id, common.packageMessageToQueue(message))
	database.rds.expire(message.channel.id +":"+ message.id, 360)

	#handoff the message to a function dedicated to its feature see also https://www.youtube.com/watch?v=ekP0LQEsUh0

	#message attachment auditing
	await auditing.attachments(message)

	#print the message to the console
	print("Channel: {0.channel} User: {0.author} (ID:{0.author.id}) Message: {0.content}".format(message))

	#http://discordpy.readthedocs.io/en/latest/faq.html#why-does-on-message-make-my-commands-stop-working
	await discord.bot.process_commands(message)
	msgProcessEnd = time.time()

	#send off message runtime avg for (quick) math
	common.bernardMessageProcessTime(msgProcessStart, msgProcessEnd)