#always import config, common, discord in that order or things will break
import bernard.config
import bernard.common
import bernard.discord
import bernard.database
import bernard.analytics

#chat modules
import bernard.hello
import bernard.administrate
import bernard.crypto

#moderation modules
import bernard.message
import bernard.auditing
import bernard.purger
import bernard.errorhandler
#import bernard.memberstate

#import bernard.antispam

#starts our threads, this should always be loaded last
import bernard.threading