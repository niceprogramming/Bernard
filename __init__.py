import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s -> %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
logger.info("Attempting to start. I can't promise you I will work but I can sure try.")

import bernard.eventloop

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
import bernard.memberstate
import bernard.deleted
import bernard.invites

logger.warn("STARTING DISCORD BOT...")
bernard.discord.bot.run(bernard.config.cfg['discord']['token'])