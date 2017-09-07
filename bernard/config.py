print("Importing... %s" % __name__)
import json

#load the json file as cfg, allows access as bernard.cfg. Stop on error.
try:
	with open("config.json", "r") as cfgFile:
		cfg = json.load(cfgFile)
except FileNotFoundError:
	print("ERROR: config.json file missing inside root folder...")
	exit()