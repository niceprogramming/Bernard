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

    try:
        for role in member.roles:
            if role.id == config.cfg['bernard']['administrators']: return True
    except AttributeError:
        return False

    return False

def datetimeObjectToString(timestamp):
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")

def bernardStartTimeSet():
    global bernardStartTimeSets
    bernardStartTimeSets = time.time()

def isDiscordMainServer(server):
    if server is None:
        return False
        
    if server.id == config.cfg['discord']['server']:
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

#this should always return a discord.User
def target_user(ctx, target=None):
    #if we only got the context we only have the context
    if target is None:
        return ctx.message.author

    #check if the user is allowed to modify the target
    if isDiscordAdministrator(ctx.message.author) is not True:
        return ctx.message.author

    #if there is a mention use that for the user objext returned
    if len(ctx.message.mentions) == 1:
        return ctx.message.mentions[0]

    #if we got this far we are working with a string of either an ID or a named member
    named = ctx.message.server.get_member_named(target)
    snowflake = ctx.message.server.get_member(target)

    #one of these should be true, if neither are return None
    if named:
        return named
    elif snowflake:
        return snowflake
    else:
        return None

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
        logger.error("common.getJSON() threw an exception: {0}".format(e))
        return None