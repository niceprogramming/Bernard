print("Importing... %s" % __name__)

from . import config
from . import discord

@discord.bot.event
async def on_message(message):
	#only reply to the guild set in config file
	if message.server.id != config.cfg['discord']['server']:
		return

	#handoff the message to a function dedicated to its feature 
	#see also https://www.youtube.com/watch?v=ekP0LQEsUh0

	#auditing-attachments.main(message)

	#print the message to the console
	print("Channel: {0.channel} User: {0.author} (ID:{0.author.id}) Message: {0.content}".format(message))

	#http://discordpy.readthedocs.io/en/latest/faq.html#why-does-on-message-make-my-commands-stop-working
	await discord.bot.process_commands(message)