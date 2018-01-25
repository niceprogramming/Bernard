from . import config
from . import common
from . import discord
from . import database
from . import analytics
from . import crypto

import sys
import os
import subprocess
import asyncio
import logging
import datetime

logger = logging.getLogger(__name__)
logger.info("loading...")

#very dangerous administration commands only plz #common.isDiscordBotOwner(ctx.message.author.id):
@discord.bot.group(pass_context=True, no_pm=True, hidden=True)
async def admin(ctx):
    if common.isDiscordAdministrator(ctx.message.author):
        if ctx.invoked_subcommand is None:
            await discord.bot.say('Invalid subcommand... ```run | git | host | modules | cfg | timings | domainblacklist')

#eval
@admin.command(pass_context=True, no_pm=True, hidden=True)
async def run(ctx, *, msg: str):
    if common.isDiscordBotOwner(ctx.message.author.id):
        try:
            evalData = eval(msg.replace('`',''))
            await discord.bot.say("```{0}```".format(evalData))
        except Exception as e:
            await discord.bot.say("```{0}```".format(e))

#get git revision
@admin.command(pass_context=True, no_pm=True, hidden=True)
async def git(ctx):
	if common.isDiscordAdministrator(ctx.message.author):
		gitcommit = subprocess.check_output(['git','rev-parse','--short','HEAD']).decode(encoding='UTF-8').rstrip()
		gitbranch = subprocess.check_output(['git','rev-parse','--abbrev-ref','HEAD']).decode(encoding='UTF-8').rstrip()
		gitremote = subprocess.check_output(['git','config','--get','remote.origin.url']).decode(encoding='UTF-8').rstrip()
		await discord.bot.say("```Commit {0}, Branch {1}, Remote {2}```".format(gitcommit, gitbranch, gitremote))

#get python version and discordpy version
@admin.command(pass_context=True, no_pm=True, hidden=True)
async def host(ctx):
	if common.isDiscordAdministrator(ctx.message.author):
		await discord.bot.say("```Discord.py {0}, Python {1} ({2})```".format(discord.discord.__version__, sys.version, sys.platform))

#print what modules have been loaded for the bot
@admin.command(pass_context=True, no_pm=True, hidden=True)
async def modules(ctx):
	if common.isDiscordAdministrator(ctx.message.author):
		mods = ""
		for k in sys.modules.keys():
			if "bernard" in k:
				mods = mods + "\n" + k
		await discord.bot.say("```{0}```".format(mods))

#reload the config in place
@admin.command(pass_context=True, no_pm=True, hidden=True, aliases=['cfg', 'reloadconfig'])
async def reloadcfg(ctx):
    if common.isDiscordAdministrator(ctx.message.author):
        if config.verify_config() is True:
            await discord.bot.say("Config file check passed. Waiting 3 seconds and in-place reloading config.json.")
            await asyncio.sleep(3)
        else:
            await discord.bot.say("Unable to reload config.json in place due to file check failure. Check console for more info.")
            return

        if config.reload_config() is True:
            await discord.bot.say("Config reload in-place sucessfully! <:pepoChamp:359903320032280577>")


#get the data for time spent message.on_message()
@admin.command(pass_context=True, no_pm=True, hidden=True)
async def timings(ctx):
	if common.isDiscordAdministrator(ctx.message.author):
		#get the avg without numpy because I dont want to import useless shit but will do it anyway in 3 months
		onMessageTimeAvg = round(sum(analytics.onMessageProcessTimes) / len(analytics.onMessageProcessTimes), 3)
		try:
			onMemberTimeAvg = round(sum(analytics.onMemberProcessTimes) / len(analytics.onMemberProcessTimes), 3)
		except ZeroDivisionError:
			onMemberTimeAvg = 0
		await discord.bot.say("```on_message() Avg: {0}s, Longest: {1}s Shortest: {2}s```".format(onMessageTimeAvg, max(analytics.onMessageProcessTimes), min(analytics.onMessageProcessTimes)))


#handle auditing_blacklist_domains control
@admin.command(pass_context=True, no_pm=True, hidden=True)
async def blacklist(ctx, command: str, domain: str, policy="delete"):
    if common.isDiscordAdministrator(ctx.message.author) is False:
        return

    if policy not in ['audit','delete','kick','ban']:
        await discord.bot.say("⚠️ {0.message.author.mention} Invalid policy! Options `audit | delete | kick | ban`".format(ctx))
        return

    if command == "add":
        #add a new domain to the DB
        database.dbCursor.execute('''SELECT * FROM auditing_blacklisted_domains WHERE domain=?''', (domain,))
        dbres = database.dbCursor.fetchone()
        if dbres == None:
            database.dbCursor.execute('''INSERT OR IGNORE INTO auditing_blacklisted_domains(domain, action, added_by, added_when) VALUES(?,?,?,?)''', (domain.lower(), policy.lower(), ctx.message.author.name, int(datetime.datetime.utcnow().timestamp())))
            database.dbConn.commit()
            await discord.bot.say("✔️ {0.message.author.mention} Domain `{1}` added with the policy: **{2}**".format(ctx, domain, policy.title()))
        else:
            await discord.bot.say("⚠️ {0.message.author.mention} Unable to add `{1}` added with the policy: **{2}** domain already exits!".format(ctx, domain, policy.title()))
    elif command == "remove":
        #delete a domain from the DB
        database.dbCursor.execute('''SELECT * FROM auditing_blacklisted_domains WHERE domain=?''', (domain,))
        dbres = database.dbCursor.fetchone()
        if dbres != None:
            database.dbCursor.execute('''DELETE FROM auditing_blacklisted_domains WHERE domain=?''', (domain,))
            database.dbConn.commit()
            await discord.bot.say("✔️ {0.message.author.mention} Domain `{1}` removed!".format(ctx, domain))
        else:
            await discord.bot.say("⚠️ {0.message.author.mention} Unable to remove `{1}` domain does not exist!".format(ctx, domain))
    elif command == "update":
        #update an existing domain with new policy
        database.dbCursor.execute('''SELECT * FROM auditing_blacklisted_domains WHERE domain=?''', (domain,))
        dbres = database.dbCursor.fetchone()
        if dbres != None:
            database.dbCursor.execute('''UPDATE auditing_blacklisted_domains SET action=? WHERE domain=?''', (policy, domain))
            database.dbConn.commit()
            await discord.bot.say("✔️ {0.message.author.mention} Domain `{1}` policy updated! Was **{2}** now **{3}**".format(ctx, domain, dbres[1].title(), policy.title()))
        else:
            await discord.bot.say("⚠️ {0.message.author.mention} Unable to modify `{1}` domain does not exist!".format(ctx, domain))
    elif command == "info":
        #display an embed with the stats
        database.dbCursor.execute('''SELECT * FROM auditing_blacklisted_domains WHERE domain=?''', (domain,))
        dbres = database.dbCursor.fetchone()
        if dbres != None:
            emd = discord.embeds.Embed(title='Auditing information for domain: "{0}"'.format(domain), color=0xE79015)
            emd.add_field(name="Domain", value=dbres[0])
            emd.add_field(name="Action", value=dbres[1].title())
            emd.add_field(name="Hits", value="{:,}".format(dbres[4]))
            emd.add_field(name="Added On", value="{} UTC".format(datetime.datetime.utcfromtimestamp(dbres[3]).isoformat()), inline=True)
            emd.add_field(name="Added By", value=dbres[2], inline=True)        
            await discord.bot.say(embed=emd)
        else:
            await discord.bot.say("⚠️ {0.message.author.mention} Domain not found in database.".format(ctx))
    else:
        await discord.bot.say("{0.message.author.mention} Available options `<add | remove | update | info>` `<domain>` `<audit | delete | kick | ban>`".format(ctx))