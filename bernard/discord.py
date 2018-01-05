print("%s loading..." % __name__) 

from . import config

import discord
from discord.ext import commands

bot = commands.Bot(command_prefix='!', description='Bernard, for Discord. Made with love by ILiedAboutCake')

@bot.event
async def on_ready():
    print('{0} Logged in as "{0.user.name} ID:{0.user.id}"'.format(__name__, bot))

def objectFactory(snowflake):
	return discord.Object(snowflake)