print("Importing... %s" % __name__)
from . import config

import sqlite3
import redis

#sqlite
dbConn = sqlite3.connect(config.cfg['bernard']['database']['sqlite'], check_same_thread=False)
dbCursor = dbConn.cursor()

#redis - yes im using database namespace for a NoSQL 
rds = redis.StrictRedis(host=config.cfg['bernard']['database']['redis']['host'], port=config.cfg['bernard']['database']['redis']['port'], db=config.cfg['bernard']['database']['redis']['db'])