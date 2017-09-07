print("Importing... %s" % __name__)
from . import config

global config

def isDiscordBotOwner(id):
	return id == config.cfg['bernard']['owner']

def isDiscordAdministrator(roles):
	for role in roles:
		if role.id == config.cfg['bernard']['administrators']: return True