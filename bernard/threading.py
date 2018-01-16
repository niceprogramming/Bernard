from . import config
from . import common
from . import discord
from . import antispam

#from .bgtasks import test

from threading import Thread
import time
import logging

logger = logging.getLogger(__name__)
logger.info("loading...")

def discordBot():
    logger.warn("STARTING DISCORD BOT THREAD...")
    discord.bot.run(config.cfg['discord']['token'])

def antiSpamCalculator():
    logger.warn("STARTING DISCORD ANTISPAM THREAD...") 
    antispam.main()

#def testBGThread():
    #print("%s STARTING CRYPTO PUBSUB THREAD..." % __name__) 
    #test.main()


dThread = Thread(target=discordBot, name="Discord.PY bot thread")
#aThread = Thread(target=antiSpamCalculator, name="Anti-spam calcuation thread")
#tThread = Thread(target=testBGThread, name="test thread")

dThread.start()
#tThread.start()
#aThread.start()