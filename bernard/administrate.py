print("Importing... %s" % __name__)

from . import config
from . import common
from . import discord
from . import database
from . import analytics
from . import crypto

import sys
import os
import subprocess

#very dangerous administration commands only plz #common.isDiscordBotOwner(ctx.message.author.id):
@discord.bot.group(pass_context=True, no_pm=True, hidden=True)
async def admin(ctx):
    if common.isDiscordAdministrator(ctx.message.author.roles):
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

#raw sql commands, another stupid and dangerous command to be allowed by normies
#@admin.command(pass_context=True, no_pm=True, hidden=True)
#async def run(ctx, *, query: str):
#    if common.isDiscordBotOwner(ctx.message.author.id):


#get git revision
@admin.command(pass_context=True, no_pm=True, hidden=True)
async def git(ctx):
	if common.isDiscordAdministrator(ctx.message.author.roles):
		gitcommit = subprocess.check_output(['git','rev-parse','--short','HEAD']).decode(encoding='UTF-8').rstrip()
		gitbranch = subprocess.check_output(['git','rev-parse','--abbrev-ref','HEAD']).decode(encoding='UTF-8').rstrip()
		gitremote = subprocess.check_output(['git','config','--get','remote.origin.url']).decode(encoding='UTF-8').rstrip()
		await discord.bot.say("```Commit {0}, Branch {1}, Remote {2}```".format(gitcommit, gitbranch, gitremote))

#get python version and discordpy version
@admin.command(pass_context=True, no_pm=True, hidden=True)
async def host(ctx):
	if common.isDiscordAdministrator(ctx.message.author.roles):
		await discord.bot.say("```Discord.py {0}, Python {1} ({2})```\n🐍🐍🐍🐍🐍".format(discord.discord.__version__, sys.version, sys.platform))

#print what modules have been loaded for the bot
@admin.command(pass_context=True, no_pm=True, hidden=True)
async def modules(ctx):
	if common.isDiscordAdministrator(ctx.message.author.roles):
		mods = ""
		for k in sys.modules.keys():
			if "bernard" in k:
				mods = mods + "\n" + k
		await discord.bot.say("```{0}```".format(mods))

#get the data for time spent message.on_message()
@admin.command(pass_context=True, no_pm=True, hidden=True)
async def timings(ctx):
	if common.isDiscordAdministrator(ctx.message.author.roles):
		#get the avg without numpy because I dont want to import useless shit but will do it anyway in 3 months
		onMessageTimeAvg = round(sum(analytics.onMessageProcessTimes) / len(analytics.onMessageProcessTimes), 3)
		try:
			onMemberTimeAvg = round(sum(analytics.onMemberProcessTimes) / len(analytics.onMemberProcessTimes), 3)
		except ZeroDivisionError:
			onMemberTimeAvg = 0
		await discord.bot.say("```on_message() Avg: {0}s, Longest: {1}s Shortest: {2}s```".format(onMessageTimeAvg, max(analytics.onMessageProcessTimes), min(analytics.onMessageProcessTimes)))