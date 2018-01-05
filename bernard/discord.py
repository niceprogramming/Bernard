print("%s loading..." % __name__) 

from . import config

import asyncio
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix='!', description='Bernard, for Discord. Made with love by ILiedAboutCake')

@bot.event
async def on_ready():
    print('{0} Logged in as "{1.user.name} ID:{1.user.id}"'.format(__name__, bot))
    await asyncio.sleep(5)
    
    print('{0} Setting game status as in as "{1}"'.format(__name__, config.cfg['bernard']['gamestatus']))
    await bot.change_presence(game=discord.Game(name=config.cfg['bernard']['gamestatus']))

def objectFactory(snowflake):
	return discord.Object(snowflake)