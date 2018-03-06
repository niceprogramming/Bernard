from . import config
from . import common
from . import discord

import logging

logger = logging.getLogger(__name__)
logger.info("loading...")

#hello.py - for basic bot health check commands and simple condition checks is admin / is owner etc

#!hello = ping/pong with more wit :)
@discord.bot.command(pass_context=True, no_pm=True, description="Says Hello :)")
async def hello(ctx):
    await discord.bot.say("Hello {0.message.author.mention}! I am alive and well <:DestiSenpaii:399640604557967380>".format(ctx))

#!isowner = sanity check for ownership for dangerous commands
@discord.bot.command(pass_context=True, no_pm=True, hidden=True)
async def isowner(ctx):
    if common.isDiscordBotOwner(ctx.message.author.id):
        await discord.bot.say("I live to please {0.message.author.mention} every way possible ( ͡° ͜ʖ ͡°)".format(ctx))

#!isadmin = sanity check for administration commands access
@discord.bot.command(pass_context=True, no_pm=True, hidden=True)
async def isadmin(ctx):
    if common.isDiscordAdministrator(ctx.message.author):
        await discord.bot.say("Somehow Destiny let you have administrator in here... {0.message.author.mention}".format(ctx)) 

#!isregulator = sanity check for regulators to confirm their power level
@discord.bot.command(pass_context=True, no_pm=True, hidden=True)
async def isregulator(ctx):
    if common.isDiscordRegulator(ctx.message.author):
        await discord.bot.say("{0.message.author.mention} is a regulator, and is ready to abuse all powers granted by the admins™.".format(ctx))