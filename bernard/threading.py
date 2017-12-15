print("Importing... %s" % __name__)

from . import config
from . import common
from . import discord
from . import antispam

from threading import Thread
import time

def discordBot():
	print('!!!!! STARTING BOT THREAD !!!!!')
	discord.bot.run(config.cfg['discord']['token'])

def antiSpamCalculator():
	print('!!!!! STARTING ANTI-SPAM THREAD !!!!!')
	antispam.main()


dThread = Thread(target=discordBot, name="Discord.PY bot thread")
#aThread = Thread(target=antiSpamCalculator, name="Anti-spam calcuation thread")

dThread.start()
#aThread.start()