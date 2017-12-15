print("Importing... %s" % __name__)

from . import config
from . import common
from . import database

import json

#for more info on how some of this code works, see https://xkcd.com/208/ and https://xkcd.com/323/
#see common.py for packageMessageToQueue(msg) which returns what we have to work with
''' 
msgDict = {
	"timestamp":datetimeObjectToString(msg.timestamp),
	"content":msg.content,
	"embeds":msg.embeds,
	"attachments":msg.attachments,
	"member": {
		"joined":datetimeObjectToString(msg.author.joined_at),
		"nick":msg.author.nick,
		"author": str(msg.author),
		"top_role":msg.author.top_role.id,
		},
	"scored":0,
	"score":0
}

'''

def main():
	sub = database.rds.pubsub()
	sub.subscribe("AntiSpam")

	#message handler

	#when you look at this again dumbass its sending 1 when the pubsub starts and json.loads() loses its fucking mind over an int

	for msg in sub.listen():
		print(msg['data'])
		if msg['data'] != 1:
			memes = json.loads(msg['data'])

		print(memes['timestamp'])

		#attachmentsHandler(msg['data']['attachments'])

def messageToDict(msg):
	return json.loads(msg)

def attachmentsHandler(attach):
	print(attach)