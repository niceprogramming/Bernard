from . import config
from . import common
from . import discord

import time
import logging
import numpy

logger = logging.getLogger(__name__)
logger.info("loading...")

onMessageProcessTimes = [] #def bernardMessageProcessTime(start, end):
onMemberProcessTimes = [] #def analytics.onMemberProcessTime(start, end):
bernardLastMessageChannels = {}
genesis = 0
messages_processed = 0
messages_processed_perchannel = {}
messages_processed_users = {}

def onMessageProcessTime(start, end):
	global onMessageProcessTimes
	#pop the oldest in the array
	if len(onMessageProcessTimes) >= 1000:
		onMessageProcessTimes.pop(0)
	onMessageProcessTimes.append(round(end - start, 3))

def onMemberProcessTime(start, end):
	global onMemberProcessTimes
	if len(onMemberProcessTimes) >= 1000:
		onMemberProcessTimes.pop(0)
	onMemberProcessTimes.append(round(end - start, 3))

def get_onMessageProcessTime():
    avg = numpy.average(onMessageProcessTimes)
    pcntle = numpy.percentile(onMessageProcessTimes, 95)
    high = max(onMessageProcessTimes)
    low = min(onMessageProcessTimes)
    count = len(onMessageProcessTimes)
    return "Last {} events: *AVG*: {:.3f}ms *95TH*: {:.1f}ms *WORST*: {:.1f}ms *BEST*: {:.1f}ms".format(count, avg*100, pcntle*100, high*100, low*100)

def get_onMemberProcessTime():
    avg = numpy.average(onMemberProcessTimes)
    pcntle = numpy.percentile(onMemberProcessTimes, 95)
    high = max(onMemberProcessTimes)
    low = min(onMemberProcessTimes)
    count = len(onMemberProcessTimes)
    return "Last {} events: *AVG*: {:.3f}ms *95TH*: {:.1f}ms *WORST*: {:.1f}ms *BEST*: {:.1f}ms".format(count, avg*100, pcntle*100, high*100, low*100)

def getEventTime():
	return time.time()

def setGenesis():
	global genesis
	genesis = getEventTime()
	return genesis

#get a friendly string of how long the bot has been online
def getRuntime():
    runtime = getEventTime() - genesis

    if runtime > 86400:
        days, rem = divmod(runtime, 86400)
        hours, rem = divmod(rem, 3600)
        mins, secs = divmod(rem, 60)
        return "Up {} days, {:02d}:{:02d}".format(int(days), int(hours), int(mins))
    elif runtime > 3600:
        hours, rem = divmod(runtime, 3600)
        mins, secs = divmod(rem, 60)
        return "Up {:02d}:{:02d}".format(int(hours), int(mins))
    else:
        mins, secs = divmod(runtime, 60)
        return "Up {:01d} Minutes {:02d} Seconds".format(int(mins), int(secs))

#keep track of how messages processed since genesis
def setMessageCounter(msg):
    global messages_processed
    messages_processed = messages_processed+1

    try:
        messages_processed_perchannel[msg.channel.id] += 1
    except KeyError:
        messages_processed_perchannel[msg.channel.id] = 1

    try:
        messages_processed_users[msg.author.id] += 1
    except KeyError:
        messages_processed_users[msg.author.id] = 1

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