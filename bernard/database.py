print("Importing... %s" % __name__)
from . import config

import sqlite3

dbConn = sqlite3.connect(config.cfg['bernard']['database'])
dbCursor = dbConn.cursor()