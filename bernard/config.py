print("%s loading..." % __name__) 
import sys
import json
import copy
import os

CONFIG_FILE = "config.json"

def verify_config():
    if os.path.isfile(CONFIG_FILE) is False:
        print("{0}: FATAL: config.json does not exist in root folder.".format(__name__))        
        return False

    with open(CONFIG_FILE, "r") as cfgRead:
        try:
            json.load(cfgRead)
            return True
        except ValueError as e:
            print("{0}: FATAL: config.json is not formatted properly {1}".format(__name__,e))
            return False

#load the json file as cfg, allows access as config.json. Stop on error.
def start_config():
    global cfg
    if verify_config():
        with open(CONFIG_FILE, "r") as cfgFile:
            cfg = json.load(cfgFile)
            print("{0}: INFO: config.json loaded in bot genesis.".format(__name__))
            return True
    else:
        print("{0}: FATAL: Unable to start bot. Unrecoverable error in loading genesis configuration file.".format(__name__))
        sys.exit(0)

def reload_config():
    global cfg
    if verify_config():
        del cfg
        with open(CONFIG_FILE, "r") as cfgFile:
            cfg = json.load(cfgFile)
            print("{0}: INFO: config.json reloaded in place.".format(__name__))
            return True

start_config()