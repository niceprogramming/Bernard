from . import config
from . import common
from . import database

import re
import json
import logging
import antispam as antispam_external

logger = logging.getLogger(__name__)
logger.info("loading...")

#for more info on how some of this code works, see https://xkcd.com/208/ and https://xkcd.com/323/
#CREATE TABLE `antispam_rawvalues` ( `url_count` INTEGER, `url_count_unique` INTEGER, `bayesian_score` REAL, `user_mentions` INTEGER, `user_mentions_unique` INTEGER, `emote_count` INTEGER, `emote_count_unique` INTEGER, `everyone_mention` INTEGER, `word_count` INTEGER, `word_count_unique` INTEGER, `message` INTEGER, `messageid` INTEGER UNIQUE, PRIMARY KEY(`messageid`) )
class antispam_auditor:
    def __init__(self, message):
        self.message = message
        self.scored = 0

    def score(self):
        self.count_urls()
        self.bayesian_score_generic()
        self.count_user_mentions()
        self.count_emotes()
        self.find_ateveryone()
        self.count_words()

        #logger.info("{0} {1} {2} {3} {4} {5} {6} {7} {8}".format(self.user_mentions, self.user_mentions_unique, self.bayesian_score, self.user_mentions, self.user_mentions_unique, self.emotes, self.emotes_unique, self.wordcount, self.wordunique))

        #database.dbCursor.execute('''INSERT INTO antispam_rawvalues(url_count, url_count_unique, bayesian_score, user_mentions, user_mentions_unique, emote_count) VALUES(?,?,?,?)''', (ticker.lower(), alias.lower(), analytics.getEventTime(), ctx.message.author.name))

    def count_urls(self):
        full_urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', self.message.content)
        self.url_count = len(full_urls)
        self.url_count_unique = len(list(set(full_urls)))

    #https://pypi.python.org/pypi/antispam
    def bayesian_score_generic(self):
        try:
            scored = antispam_external.score(self.message.content)
        except:
            scored = 0

        self.bayesian_score = scored

    #count how many mentions there are, then count how many UNIQUE people are mentioned
    def count_user_mentions(self):
        full = re.findall('<@[0-9]*>', self.message.content)
        self.user_mentions = len(full)
        self.user_mentions_unique = len(list(set(full)))

    #count how many emotes are there, then count how many UNIQUE emotes were used
    def count_emotes(self):
        full = re.findall('<:(.*?):[0-9]*>', self.message.content)
        self.emotes = len(full)
        self.emotes_unique = len(list(set(full)))

    #look for @everyone or @here, this should auto kick if not an admin tbh
    def find_ateveryone(self):
        full = re.findall('@everyone|@here', self.message.content)
        if len(full) == 0:
            self.ateveryone = 0
        else:
            self.ateveryone = 1

    #count how many words are in the message, how many are unique words over 2 chars
    def count_words(self):
        words_list = self.message.content.split()
        words_set = set(words_list)
        self.wordcount = len(words_list)
        self.wordunique = len(words_set)