from . import config
from . import common
from . import discord
from . import database

import logging
import asyncio
import time

logger = logging.getLogger(__name__)
logger.info("loading...")

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