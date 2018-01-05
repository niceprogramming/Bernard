print("%s loading..." % __name__) 

from . import config
from . import common
from . import discord

import time

onMessageProcessTimes = [] #def bernardMessageProcessTime(start, end):
onMemberProcessTimes = [] #def analytics.onMemberProcessTime(start, end):
bernardLastMessageChannels = {}
bernardGenesis = 0

def onMessageProcessTime(start, end):
	global onMessageProcessTimes
	#pop the oldest in the array
	if len(onMessageProcessTimes) >= 20:
		onMessageProcessTimes.pop(0)
	onMessageProcessTimes.append(round(end - start, 3))

def onMemberProcessTime(start, end):
	global onMemberProcessTimes
	if len(onMemberProcessTimes) >= 20:
		onMemberProcessTimes.pop(0)
	onMemberProcessTimes.append(round(end - start, 3))

def getEventTime():
	return time.time()

def setGenesis():
	global bernardGenesis
	bernardGenesis = getEventTime()
	return bernardGenesis

#create a dict of all channels and the last time the bot spoke in the channel
def rateLimitNewMessage(channel, eventTime):
	bernardLastMessageChannels[channel] = int(eventTime) #cast the float to an int, add it to a dictionary for all channels

#find the last time the bot spoke in channel, if the bot has never spoken since boot return the ratelimit in config.json
def rateLimitSinceLastMessage(channel):
	try:
		return int(getEventTime()) - bernardLastMessageChannels[channel]
	except KeyError:
		return config.cfg['bernard']['ratelimit']

#controls if we should process commands or not
def rateLimitAllowProcessing(msg):
	last = rateLimitSinceLastMessage(msg.channel.id)
	if common.isDiscordAdministrator(msg.author):
		return True
	elif last >= config.cfg['bernard']['ratelimit']:
		return True
	else:
		return False

setGenesis()