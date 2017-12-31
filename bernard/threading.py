print("%s loading..." % __name__) 

from . import config
from . import common
from . import discord
from . import antispam

#from .bgtasks import test

from threading import Thread
import time

def discordBot():
    print("%s STARTING DISCORD BOT THREAD..." % __name__) 
    discord.bot.run(config.cfg['discord']['token'])

def antiSpamCalculator():
    print("%s STARTING DISCORD ANTISPAM THREAD..." % __name__) 
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