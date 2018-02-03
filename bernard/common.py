from . import config

import datetime
import time
import json
import aiohttp
import logging

logger = logging.getLogger(__name__)
logger.info("loading...")

bernardStartTimeSets = 0

def isDiscordBotOwner(id):
    return id == config.cfg['bernard']['owner']

def isDiscordAdministrator(member):
    if isDiscordBotOwner(member.id): return True

    for role in member.roles:
        if role.id == config.cfg['bernard']['administrators']: return True

    return False

def datetimeObjectToString(timestamp):
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")

def bernardStartTimeSet():
    global bernardStartTimeSets
    bernardStartTimeSets = time.time()

def packageMessageToQueue(msg):
    try:
        joined_at = datetimeObjectToString(msg.author.joined_at)
    except AttributeError:
        joined_at = None

    msgDict = {
        "timestamp":datetimeObjectToString(msg.timestamp),
        "content":msg.content,
        "embeds":msg.embeds,
        "attachments":msg.attachments,
        "member": {
            "joined":joined_at,
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

def bernardAccountAgeToFriendly(user):
    diff = int(datetime.datetime.utcnow().timestamp() - user.created_at.timestamp())

    years, rem = divmod(diff, 31104000)
    months, rem = divmod(rem, 2592000)
    days, rem = divmod(rem, 86400)
    hours, rem = divmod(rem, 3600)
    mins, secs = divmod(rem, 60)

    return "{:02d}:{:02d}:{:02d}:{:02d}:{:02d}:{:02d}".format(years, months, days, hours, mins, secs)

async def getJSON(url, tmout=5, hdrs=None):
    logger.info("common.getJSON() attempting async URL {0} Timeout:{1}s".format(url, tmout))
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=tmout, headers=hdrs) as r:
                logger.info("common.getJSON() returned HTTP/{}".format(r.status))
                if r.status == 200:
                    if "application/json" in r.headers['Content-Type']: 
                        ret = await r.json()
                        return ret
                    else:
                        logger.warn("common.getJSON() unable to get JSON from endpoint. Content-Type mismatched {}".format(r.headers['Content-Type']))
                        return None
                else:
                    logger.warn("common.getJSON() unable to get JSON from endpoint. HTTP code not valid HTTP/{}".format(r.status))
                    return None
    except Exception as e:
        logging.error("common.getJSON() threw an excpetion: {0}".format(e))
        return None