print("Importing... %s" % __name__)
from . import config

import datetime

global config

def isDiscordBotOwner(id):
	return id == config.cfg['bernard']['owner']

def isDiscordAdministrator(roles):
	for role in roles:
		if role.id == config.cfg['bernard']['administrators']: return True

def datetimeObjectToString(timestamp):
	return timestamp.strftime("%Y-%m-%d %H:%M:%S")