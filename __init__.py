#always import config, common, discord in that order or things will break
import bernard.config
import bernard.common
import bernard.discord
import bernard.database

#chat modules
import bernard.hello
import bernard.administrate

#moderation modules
import bernard.message

#start the discord connection
bernard.discord.bot.run(bernard.config.cfg['discord']['token'])