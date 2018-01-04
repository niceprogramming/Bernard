print("Importing... %s" % __name__)
from . import config

import datetime
import time
import json
import aiohttp

global config


bernardStartTimeSets = 0

def isDiscordBotOwner(id):
	return id == config.cfg['bernard']['owner']

def isDiscordAdministrator(member):
	if isDiscordBotOwner(member.id): return True

	for role in member.roles:
		if role.id == config.cfg['bernard']['administrators']: return True

def datetimeObjectToString(timestamp):
	return timestamp.strftime("%Y-%m-%d %H:%M:%S")

def bernardStartTimeSet():
	global bernardStartTimeSets
	bernardStartTimeSets = time.time()

def packageMessageToQueue(msg):
	msgDict = {
		"timestamp":datetimeObjectToString(msg.timestamp),
		"content":msg.content,
		"embeds":msg.embeds,
		"attachments":msg.attachments,
		"member": {
			"joined":datetimeObjectToString(msg.author.joined_at),
			"nick":msg.author.nick,
			"author": str(msg.author),
			"top_role":msg.author.top_role.id,
			},
		"scored":0,
		"score":0
	}
	msgToQueue = json.dumps(msgDict)
	return(msgToQueue)

def isDiscordMainServer(id):
	if id == config.cfg['discord']['server']:
		return True

def bernardUTCTimeNow():
    return datetime.datetime.utcnow().strftime(config.cfg["bernard"]["timestamp"])

def bernardTimeToEpoch(age):
	return datetime.datetime(age).timestamp()

def bernardAccountAgeToFriendly(epoch):
	diff = time.time() - epoch

	years, rem = divmod(diff, 31104000)
	months, rem = divmod(rem, 2592000)
	days, rem = divmod(rem, 86400)
	hours, rem = divmod(rem, 3600)
	mins, secs = divmod(rem, 60)

	years = int(years)
	months = int(months)
	days = int(days)
	hours = int(hours)
	mins = int(mins)
	secs = int(secs)

	if years >= 1:
		return "{}Yr {}Mo {}Day".format(years, months, days)
	elif months >= 1:
		return "{}Mo {}Day {}Hr".format(months, days, hours)
	elif days >= 1:
		return "{}Day {}Hr {}Min".format(days, hours, mins)
	elif hours >= 1:
		return "{}Hr {}Min {}Sec".format(hours, mins, secs)
	else:
		return "{}Min {}Sec".format(mins, secs)

	#return years, months, days, hours, mins, secs

async def getJSON(url, tmout=5):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=tmout) as r:
                if r.status == 200:
                    ret = await r.json()
                    return ret
                else:
                    return None
    except Exception as e:
        print(e)
        return None