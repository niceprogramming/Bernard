from . import config
from . import common
from . import discord
from . import database

from datetime import datetime

import logging
import asyncio
import time

logger = logging.getLogger(__name__)
logger.info("loading...")

#handle auditing_blacklist_domains control
@discord.bot.command(pass_context=True, hidden=True)
async def journal(ctx, user: str):
    if common.isDiscordAdministrator(ctx.message.author) is False:
        return

    try:
        member = ctx.message.mentions[0]
    except IndexError:
        member = ctx.message.server.get_member(user)
        if member is None:
            member = ctx.message.server.get_member_named(user)

    if member is None:
        database.dbCursor.execute('''SELECT * from journal_events WHERE userid=? ORDER BY time DESC LIMIT 5''', (user,))
        emd = discord.embeds.Embed(title='Last 5 events for ({0})'.format(user), color=0xE79015)
    else:
        database.dbCursor.execute('''SELECT * from journal_events WHERE userid=? ORDER BY time DESC LIMIT 5''', (member.id,))
        emd = discord.embeds.Embed(title='Last 5 events for "{0.name}" ({0.id})'.format(member), color=0xE79015)

    dbres = database.dbCursor.fetchall()

    if len(dbres) == 0:
        await discord.bot.say("Not found in my journal :(")
        return
    else:
        for row in dbres:
            emd.add_field(inline=False,name="{}".format(datetime.fromtimestamp(int(row[2])).isoformat()), value="{0[1]} Results: {0[5]}\n".format(row))
        await discord.bot.say(embed=emd)


#CREATE TABLE "journal_jobs" ( `jobid` INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, `module` TEXT, `job` TEXT, `time` INTEGER, `runtime` INTEGER, `result` TEXT )
def update_journal_job(**kwargs):
    module = kwargs['module']
    job = kwargs['job']
    start = kwargs['start']
    result = kwargs['result']
    runtime = round(time.time() - start, 4)

    database.dbCursor.execute('''INSERT OR IGNORE INTO journal_jobs(module, job, time, runtime, result) VALUES(?,?,?,?,?)''', (module, job, time.time(), runtime, result))
    database.dbConn.commit()

#CREATE TABLE `journal_events` ( `jobid` INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, `module` TEXT, `event` TEXT, `userid` TEXT, `eventid` TEXT UNIQUE, `contents` TEXT )
def update_journal_event(**kwargs):
    module = kwargs['module']
    event = kwargs['event']
    userid = kwargs['userid']
    try:
        eventid = kwargs['eventid']
    except KeyError:
        eventid = None
    contents = kwargs['contents']

    database.dbCursor.execute('''INSERT OR IGNORE INTO journal_events(module, event, time, userid, eventid, contents) VALUES(?,?,?,?,?,?)''', (module, event, time.time(), userid, eventid, contents))
    database.dbConn.commit()