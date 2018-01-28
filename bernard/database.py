from . import config

import sqlite3
import logging

logger = logging.getLogger(__name__)
logger.info("loading...")

#sqlite
dbConn = sqlite3.connect(config.cfg['bernard']['database']['sqlite'], check_same_thread=False)
dbCursor = dbConn.cursor()