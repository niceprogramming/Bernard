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

async def get_all_invites():
    invites = await common.getJSON(config.cfg['discord']['endpoint']+"/guilds/"+config.cfg['discord']['server']+"/invites", 5, {'Authorization':'Bot ' + config.cfg['discord']['token']})
    return invites

async def on_member_leave_invite_cleanup(member):
    logger.info("on_member_leave_invite_cleanup() starting on user ID {0.id} for leaving server".format(member))
    invites = await get_all_invites()
    for invite in invites:
        if invite['inviter']['id'] == member.id:
            logger.warn("Removing invite {0[code]} due to departure from {0[inviter][username]} ({0[inviter][id]}) / {0[uses]} uses".format(invite))
            await discord.bot.send_message(discord.mod_channel(), " {0} **Removed Invite:** `{1[code]}` **From:** <@{1[inviter][id]}> (ID: `{1[inviter][id]}`) **Uses:** `{1[uses]}`".format(common.bernardUTCTimeNow(), invite))
            await discord.bot.delete_invite(invite['code'])
            await asyncio.sleep(3)

async def invite_cleanup():
    await discord.bot.wait_until_ready()
    while not discord.bot.is_closed:
        job_start = analytics.getEventTime()
        logger.info("Starting background task invite_cleanup() - Interval {0}".format(config.cfg['invite_cleanup']['interval']))
        invites = await get_all_invites()
        utc_epoch = datetime.datetime.utcnow().timestamp()
        invites_removed = 0
        for invite in invites:
            #ignore invites that already have a death
            if invite['max_age'] != 0:
                continue

            #convert the Discord datetime string into a unix epoch for easy comparison in seconds
            expire_epoch = int(time.mktime(time.strptime(invite['created_at'], config.cfg['discord']['timestamp_format'])))

            #get the amount of seconds the invite has been around, and convert it to days.
            time_alive = int((utc_epoch - expire_epoch) / 86400)

            #if its lifetime has not met faith yet we can ignore the invite
            if time_alive <= config.cfg['invite_cleanup']['lifetime']:
                continue

            #if its lifetime has met, but users are keeping it alive
            if invite['uses'] > config.cfg['invite_cleanup']['ignore_if_used_times']:
                continue

            #if we made it this far, I got bad news invite :/
            logger.warn("Removing invite {0[code]} for stale/inactivity reasons from {0[inviter][username]} ({0[inviter][id]}) {1} days old / {0[uses]} uses".format(invite, time_alive))
            await discord.bot.send_message(discord.mod_channel(), " {0} **Pruned Invite:** `{1[code]}` **From:** <@{1[inviter][id]}> (ID: `{1[inviter][id]}`) **Uses:** `{1[uses]}` **Age:** `{2}` days old".format(common.bernardUTCTimeNow(), invite, time_alive))
            await discord.bot.delete_invite(invite['code'])
            invites_removed = invites_removed+1
            await asyncio.sleep(3)

        journal.update_journal_job(module=__name__, job="invite_cleanup", start=job_start, result="{} deleted".format(invites_removed))
        logger.info("Sleeping background task invite_cleanup() - Interval {0}".format(config.cfg['invite_cleanup']['interval']))
        await asyncio.sleep(config.cfg['invite_cleanup']['interval'])

if config.cfg['invite_cleanup']['enable']:
    discord.bot.loop.create_task(invite_cleanup())