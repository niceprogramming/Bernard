print("Importing... %s" % __name__)

from . import config

import discord
from discord.ext import commands

bot = commands.Bot(command_prefix='!', description='Bernard, for Discord. Made with love by ILiedAboutCake')

@bot.event
async def on_ready():
    print('Logged in as "%s" ID:%s' % (bot.user.name, bot.user.id))

def objectFactory(snowflake):
	return discord.Object(snowflake)