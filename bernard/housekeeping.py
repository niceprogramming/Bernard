from . import config
from . import common
from . import discord
from . import analytics
from . import journal

import logging
import asyncio

logger = logging.getLogger(__name__)
logger.info("loading...")

#cleans up the server of users who have not signed into discord in x days as defined in config.cfg -> purge_inactive_users
async def purge_inactive_users():
    await discord.bot.wait_until_ready()
    while not discord.bot.is_closed:
        job_start = analytics.getEventTime()
        logger.info("Starting background task purge_inactive_users() - Interval {0}".format(config.cfg['purge_inactive_users']['interval']))

        est = await discord.bot.estimate_pruned_members(server=discord.objectFactory(config.cfg['discord']['server']), days=config.cfg['purge_inactive_users']['inactive_days'])
        if est > 0:
            #send the cleanup
            pruned = await discord.bot.prune_members(server=discord.objectFactory(config.cfg['discord']['server']), days=config.cfg['purge_inactive_users']['inactive_days'])

            #notify via mod room and console log whos getting purged
            logger.warn("Purging {0} inactive users via purge_inactive_users() background job".format(pruned))            
            await discord.bot.send_message(discord.mod_channel(), "{0} **Pruned Inactive Users:** {1} users removed for inactivity of {2} days".format(common.bernardUTCTimeNow(), pruned, config.cfg['purge_inactive_users']['inactive_days']))

        logger.info("Sleeping background task purge_inactive_users() - Interval {0}".format(config.cfg['purge_inactive_users']['interval']))
        journal.update_journal_job(module=__name__, job="purge_inactive_users", start=job_start, result=est)
        await asyncio.sleep(config.cfg['purge_inactive_users']['interval'])

if config.cfg['purge_inactive_users']['enable']:
    discord.bot.loop.create_task(purge_inactive_users())