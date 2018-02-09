from . import config
from . import common
from . import discord
from . import database
from . import auditing
from . import analytics
from . import antispam

import logging

logger = logging.getLogger(__name__)
logger.info("loading...")

@discord.bot.event
async def on_message(message):
	msgProcessStart = analytics.getEventTime()
	#only reply to the guild set in config file
	try:
		if common.isDiscordMainServer(message.server) is not True:
			await discord.bot.process_commands(message)
			return
	except AttributeError: #process messages anyway
		await discord.bot.process_commands(message)
		return

	#scan the message for spammy content
	antispam_obj = antispam.antispam_auditor(message)
	antispam_obj.score()

	#get some basic stats of message sending
	analytics.setMessageCounter(message)

	#handoff the message to a function dedicated to its feature see also https://www.youtube.com/watch?v=ekP0LQEsUh0 DO NOT AUDIT OURSELVES BAD THINGS HAPPEN
	if message.author.id != discord.bot.user.id:
		await auditing.attachments(message) #message attachment auditing
		await auditing.discord_invites(message) #discord invites
		await auditing.blacklisted_domains(message) #url blacklisting

	#print the message to the console
	if config.cfg['bernard']['debug']:
		logger.info("Channel: {0.channel} User: {0.author} (ID:{0.author.id}) Message: {0.content}".format(message))

	#handle message processing per rate limit, do not reply to ourselves
	if analytics.rateLimitAllowProcessing(message):
		if message.author.id != discord.bot.user.id:
			await discord.bot.process_commands(message)

	#set the rate limit
	if message.author.id == discord.bot.user.id:
		analytics.rateLimitNewMessage(message.channel.id, analytics.getEventTime())

	#message processing timings
	analytics.onMessageProcessTime(msgProcessStart, analytics.getEventTime())