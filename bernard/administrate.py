print("Importing... %s" % __name__)

from . import config
from . import common
from . import discord

import sys
import os

#very dangerous administration commands only plz #common.isDiscordBotOwner(ctx.message.author.id):
@discord.bot.group(pass_context=True, no_pm=True, hidden=True)
async def admin(ctx):
    if common.isDiscordBotOwner(ctx.message.author.id):
        if ctx.invoked_subcommand is None:
            await discord.bot.say('Invalid subcommand...')

#eval
@admin.command(pass_context=True, no_pm=True, hidden=True)
async def run(ctx, *, msg: str):
    if common.isDiscordBotOwner(ctx.message.author.id):
        try:
            evalData = eval(msg.replace('`',''))
            await discord.bot.say("```{0}```".format(evalData))
        except Exception as e:
            await discord.bot.say("```{0}```".format(e))
