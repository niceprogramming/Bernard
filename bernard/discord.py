from . import config

import asyncio
import discord
import logging

from discord.ext import commands
from discord import embeds

logger = logging.getLogger(__name__)
logger.info("loading...")

bot = commands.Bot(command_prefix='!', max_messages=config.cfg['bernard']['messagecache'], description='Bernard, for Discord. Made with love by ILiedAboutCake')

@bot.event
async def on_ready():
    logger.info('Logged in as "{0.user.name} ID:{0.user.id}"'.format(bot))
    await asyncio.sleep(5)

    logger.info('Setting game status as in as "{0}"'.format(config.cfg['bernard']['gamestatus']))
    await bot.change_presence(game=discord.Game(name=config.cfg['bernard']['gamestatus']))

    bot.remove_command('help')


def objectFactory(snowflake):
	return discord.Object(snowflake)