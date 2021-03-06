from . import config
from . import common
from . import discord
from . import analytics

import asyncio
import logging

logger = logging.getLogger(__name__)
logger.info("loading...")

@discord.bot.command(pass_context=True, hidden=True)
async def purgeuser(ctx, snowflake: str):
    if common.isDiscordAdministrator(ctx.message.author) is not True:
        return

    await discord.bot.say("Job starting on <@{0}> ID. Sending you a DM once this job is completed.".format(snowflake))

    start = analytics.getEventTime()
    counter = 0

    for channel in ctx.message.server.channels:
        if channel.type == discord.discord.ChannelType.text:
            logger.info("starting job on channel {0} for id {1}".format(channel, snowflake))
            async for message in discord.bot.logs_from(channel, limit=500000):
                if message.author.id == snowflake:
                    logger.debug("deleting message in {0} for id {1}".format(channel, snowflake))
                    counter += 1
                    await discord.bot.delete_message(message)
                    await asyncio.sleep(0.3)
            
    time = analytics.getEventTime() - start
    await discord.bot.send_message(ctx.message.author, "Cleanup on <@{0}> completed: Deleted {1} messages in {2} seconds.".format(snowflake, counter, int(time)))