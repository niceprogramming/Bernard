from . import config

import sqlite3
import logging
import time

logger = logging.getLogger(__name__)
logger.info("loading...")

#sqlite
dbConn = sqlite3.connect(config.cfg['bernard']['database']['sqlite'], check_same_thread=False, timeout=config.cfg['bernard']['database']['timeout'])
dbCursor = dbConn.cursor()

#check if the db is locked 
def check_db_lock():
    try:
        dbCursor.execute("SELECT * FROM journal_jobs")
        result = dbCursor.fetchall()

        dbCursor.execute('INSERT INTO journal_jobs(module, job, time, runtime, result) VALUES(?,?,?,?,?)', (__name__, "sql_health", time.time(), 0, "OK"))
        dbConn.commit()

    except sqlite3.OperationalError:
        logger.critical("Unable to start bot. Unrecoverable error in database locked.")
        exit()

check_db_lock()