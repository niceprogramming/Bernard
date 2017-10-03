print("Importing... %s" % __name__)

from . import config
from . import common
from . import discord
from . import analytics


#new member to the server. user = discord.User
@discord.bot.event
async def on_member_join(user): 
	msgProcessStart = analytics.getEventTime()
	if common.isDiscordMainServer(user.server.id) is not True:
		return

	##send the message to the admin defined channel
	await discord.bot.send_message(discord.objectFactory(config.cfg['bernard']['channel']),"{0} **New User:** {1.mention} (Name:`{1.name}#{1.discriminator}` ID:`{1.id}`) **Account Age:** {2}".format(common.bernardUTCTimeNow(), user, 	common.bernardAccountAgeToFriendly(user.created_at.timestamp())))

	analytics.onMemberProcessTime(msgProcessStart, analytics.getEventTime())

#member leaving the server. user = discord.User
@discord.bot.event
async def on_member_remove(user):
	msgProcessStart = analytics.getEventTime()
	if common.isDiscordMainServer(user.server.id) is not True:
		return

	await discord.bot.send_message(discord.objectFactory(config.cfg['bernard']['channel']),"{0} **Departing User:** {1.mention} (Name:`{1.name}#{1.discriminator}` ID:`{1.id}`)".format(common.bernardUTCTimeNow(), user))

	analytics.onMemberProcessTime(msgProcessStart, analytics.getEventTime())