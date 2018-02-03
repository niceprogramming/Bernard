from . import config
from . import common
from . import discord
from . import analytics
from . import journal

import asyncio
import datetime
import logging
import time

logger = logging.getLogger(__name__)
logger.info("loading...")

INVITE_CACHE = []

async def get_invites():
    invites = await discord.bot.invites_from(discord.bot.get_server(config.cfg['discord']['server']))
    return invites

async def invite_cache_update():
    global INVITE_CACHE
    INVITES = await get_invites()
    INVITE_CACHE = INVITES.copy()

#this might never be 100% reliable, but will be very useful in raids to mass purge or rollback spammers via a later ban command
async def on_member_join_attempt_invite_source(user):
        invites = await get_invites()

        #check to see if the invite code is cached
        for invite in invites:
            for cached_invite in INVITE_CACHE:
                if invite.code == cached_invite.code: #if the code is in cache
                    if invite.uses != cached_invite.uses: #if the uses is not the same, it was probably this user
                        journal.update_journal_event(module=__name__, event="ON_MEMBER_JOINED_WITH_INVITE", userid=user.id, contents=invite.code)
                        logger.info("Guesssing that {0.name} joined via:{1.code} from {1.inviter.name}. Usage from cache changed {2}".format(user, invite, (invite.uses - cached_invite.uses)))                        
                        return invite.code

        #update the cache. Return None if not sure
        await invite_cache_update()
        return None

async def on_member_leave_invite_cleanup(member):
    logger.info("on_member_leave_invite_cleanup() starting on user ID {0.id} for leaving server".format(member))
    invites = await get_invites()
    for invite in invites:
        if invite.inviter.id == member.id:
            logger.warn("Removing invite {0.code} due to departure from {0.inviter.name} ({0.inviter.id}) / {0.uses} uses".format(invite))
            journal.update_journal_event(module=__name__, event="ON_MEMBER_LEAVE_INVITE_CLEANUP", userid=member.id, contents="invite:{0.code} uses:{0.uses}".format(invite))
            await discord.bot.send_message(discord.mod_channel(), " {0} **Removed Invite:** `{1.code}` **From:** <@{1.inviter.id}> (ID: `{1.inviter.id}`) **Uses:** `{1.uses}`".format(common.bernardUTCTimeNow(), invite))
            await discord.bot.delete_invite(invite)
            await asyncio.sleep(3)

async def invite_cleanup():
    await discord.bot.wait_until_ready()
    while not discord.bot.is_closed:
        job_start = analytics.getEventTime()
        logger.info("Starting background task invite_cleanup() - Interval {0}".format(config.cfg['invite_cleanup']['interval']))
        invites = await get_invites()
        invites_removed = 0
        for invite in invites:
            #ignore invites that already have a death
            if invite.max_age != 0:
                continue

            #get the amount of seconds the invite has been around, and convert it to days.
            time_alive = int((datetime.datetime.utcnow().timestamp() - invite.created_at.timestamp()) / 86400)

            #if its lifetime has not met faith yet we can ignore the invite
            if time_alive <= config.cfg['invite_cleanup']['lifetime']:
                continue

            #if its lifetime has met, but users are keeping it alive
            if invite['uses'] > config.cfg['invite_cleanup']['ignore_if_used_times']:
                continue

            #if we made it this far, I got bad news invite :/
            logger.warn("Removing invite {0.code} for stale/inactivity reasons from {0.inviter.name} ({0.inviter.id}) {1} days old / {0.uses} uses".format(invite, time_alive))
            journal.update_journal_event(module=__name__, event="BACKGROUND_INVITE_CLEANUP", userid=invite.inviter.id, contents="{0.code} used:{0.uses}".format(invite))
            await discord.bot.send_message(discord.mod_channel(), " {0} **Pruned Invite:** `{1.code}` **From:** <@{1.inviter.id}> (ID: `{1.inviter.id}`) **Uses:** `{1.uses}` **Age:** `{2}` days old".format(common.bernardUTCTimeNow(), invite, time_alive))
            await discord.bot.delete_invite(invite)
            invites_removed = invites_removed+1
            await asyncio.sleep(3)

        journal.update_journal_job(module=__name__, job="invite_cleanup", start=job_start, result="{} deleted".format(invites_removed))
        logger.info("Sleeping background task invite_cleanup() - Interval {0}".format(config.cfg['invite_cleanup']['interval']))
        await asyncio.sleep(config.cfg['invite_cleanup']['interval'])

async def invite_cache_job():
    await discord.bot.wait_until_ready()
    while not discord.bot.is_closed:
        await invite_cache_update()
        await asyncio.sleep(config.cfg['invite_cleanup']['cache_interval'])

if config.cfg['invite_cleanup']['enable']:
    discord.bot.loop.create_task(invite_cleanup())

if config.cfg['invite_cleanup']['cache_enable']:
    discord.bot.loop.create_task(invite_cache_job())