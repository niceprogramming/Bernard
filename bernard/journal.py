from . import config
from . import common
from . import discord
from . import database

import logging
import asyncio

logger = logging.getLogger(__name__)
logger.info("loading...")

#CREATE TABLE "journal_jobs" ( `jobid` INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, `module` TEXT, `job` TEXT, `time` INTEGER, `runtime` INTEGER, `result` TEXT )
def update_journal_job(**kwargs):
    module = kwargs['module']
    job = kwargs['job']
    time = kwargs['time']
    start = kwargs['start']
    result = kwargs['result']
    runtime = time - start

    database.dbCursor.execute('''INSERT OR IGNORE INTO journal_jobs(module, job, time, runtime, result) VALUES(?,?,?,?,?)''', (module, job, time, runtime, result))
    database.dbConn.commit()