from . import config
from . import common
from . import discord
from . import database
from . import analytics
from . import crypto

from tabulate import tabulate

import sys
import os
import subprocess
import asyncio
import logging
import datetime
import platform

logger = logging.getLogger(__name__)
logger.info("loading...")

#very dangerous administration commands only plz #common.isDiscordBotOwner(ctx.message.author.id):
@discord.bot.group(pass_context=True, hidden=True)
async def admin(ctx):
    if common.isDiscordAdministrator(ctx.message.author):
        if ctx.invoked_subcommand is None:
            await discord.bot.say('Invalid subcommand... ```run | sql | system | modules | cfg | stats | blacklist```')

#eval
@admin.command(pass_context=True, hidden=True)
async def run(ctx, *, msg: str):
    if common.isDiscordBotOwner(ctx.message.author.id):
        emd = discord.embeds.Embed(color=0xE79015)
        try:
            evalData = eval(msg.replace('`',''))
        except Exception as e:
            evalData = e
        emd.add_field(name="Result", value=evalData)
        await discord.bot.say(embed=emd)

#sql cmd, another stupidly dangerous command
@admin.command(pass_context=True, hidden=True)
async def sql(ctx, *, sql: str):
    if common.isDiscordBotOwner(ctx.message.author.id):
        try:
            database.dbCursor.execute(sql) #dont ever do this anywhere else VERY bad and will fuck your day up
        except Exception as e:
            await discord.bot.say("```{}```".format(e))
            return

        dbres = database.dbCursor.fetchall()
        if len(dbres) is None:
            await discord.bot.say("```DB returned None.```")
            return

        #we have to get the column names then make a list of them. Then convert the list to a tuple and add it to the front of the db list. Wow.
        column_names = []
        for tb in database.dbCursor.description:
            column_names.append(tb[0])
        dbres.insert(0,tuple(column_names))

        #https://pypi.python.org/pypi/tabulate
        await discord.bot.say("```{0}```".format(tabulate(dbres, headers="firstrow")))


#get python version and discordpy version
@admin.command(pass_context=True, hidden=True)
async def system(ctx):
    if common.isDiscordAdministrator(ctx.message.author):
        load = os.times()
        gitcommit = subprocess.check_output(['git','rev-parse','--short','HEAD']).decode(encoding='UTF-8').rstrip()
        gitbranch = subprocess.check_output(['git','rev-parse','--abbrev-ref','HEAD']).decode(encoding='UTF-8').rstrip()
        gitremote = subprocess.check_output(['git','config','--get','remote.origin.url']).decode(encoding='UTF-8').rstrip().replace(".git","")

        emd = discord.embeds.Embed(color=0xE79015)
        emd.add_field(name="Discord.py Version", value=discord.discord.__version__)
        emd.add_field(name="Python Version", value=platform.python_build()[0])
        emd.add_field(name="Host", value="{} ({}) [{}] hostname '{}'".format(platform.system(), platform.platform(), sys.platform, platform.node()))
        emd.add_field(name="Process", value="PID: {} User: {:.2f}% System: {:.2f}%".format(os.getpid(), load[0]*10, load[1]*10))
        emd.add_field(name="Git Revision", value="`{}@{}` Remote: {}".format(gitcommit.upper(), gitbranch.title(), gitremote))
        await discord.bot.say(embed=emd)

#print what modules have been loaded for the bot
@admin.command(pass_context=True, hidden=True)
async def modules(ctx):
    if common.isDiscordAdministrator(ctx.message.author):
        mods = ""
        for k in sys.modules.keys():
            if "bernard" in k:
                mods = mods + "\n" + k
        emd = discord.embeds.Embed(color=0xE79015)
        emd.add_field(name="Loaded Modules", value=mods)
        await discord.bot.say(embed=emd)

#reload the config in place
@admin.command(pass_context=True, hidden=True, aliases=['cfg', 'reloadconfig'])
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
@admin.command(pass_context=True, hidden=True)
async def stats(ctx, more=None):
    if common.isDiscordRegulator(ctx.message.author) is False:
        return

    if more == None:
        #get the avg without numpy because I dont want to import useless shit but will do it anyway in 3 months <-- haha I did exactly this check git
        emd = discord.embeds.Embed(color=0xE79015)
        emd.set_thumbnail(url='https://cdn.discordapp.com/emojis/403034738979241984.png')        
        emd.add_field(name="Bot Uptime", value=analytics.getRuntime())
        emd.add_field(name="Messages Processed", value="{:,d}".format(analytics.messages_processed))
        emd.add_field(name="Unique Users", value="{:,d}".format(len(analytics.messages_processed_users)))
        emd.add_field(name="Unique Channels", value="{:,d}".format(len(analytics.messages_processed_perchannel)))
        emd.add_field(name="on_message() Statistics", value=analytics.get_onMessageProcessTime())
        emd.add_field(name="on_member() Statistics", value=analytics.get_onMemberProcessTime())
        await discord.bot.say(embed=emd)
    elif more.startswith("c"):
        sorted_channels = sorted(analytics.messages_processed_perchannel.items(), key=lambda x: x[1], reverse=True)
        msg = ""
        for channel in sorted_channels:
            msg = msg + "#{0}: {1:,d}\n".format(discord.bot.get_channel(channel[0]), channel[1])
        await discord.bot.say("Most active channels since bot reboot, {}:\n```{}```".format(analytics.getRuntime(), msg))
    elif more.startswith("u"):
        sorted_users = sorted(analytics.messages_processed_users.items(), key=lambda x: x[1], reverse=True)
        server = discord.bot.get_server(config.cfg['discord']['server'])
        msg = ""
        for user in sorted_users[:10]:
            msg = msg + "{0}: {1:,d}\n".format(server.get_member(user[0]), user[1])
        await discord.bot.say("Top 10 talkative users since bot reboot, {}:\n```{}```".format(analytics.getRuntime(), msg))
    else:
        await discord.bot.say("Unknown subcommand. Try `channel | user`")

#handle auditing_blacklist_domains control
@admin.command(pass_context=True, hidden=True)
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