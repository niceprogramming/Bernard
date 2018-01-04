print("Importing... %s" % __name__)

from . import config
from . import common
from . import discord

async def attachments(msg):
    if common.isDiscordAdministrator(msg.author) is not True:
        if msg.attachments:
            for attachment in msg.attachments:
                exploded = attachment['filename'].split(".")[1:]
                for ext in exploded:
                    ext = ext.replace(".","").replace("-","")
                    if ext in config.cfg['auditing']['attachments']['restricted']:
                        await discord.bot.delete_message(msg)
                        await discord.bot.send_message(msg.channel, "{0}, <:pepoG:352533294862172160> that file format is not allowed to be uploaded here. Filename: `{1}`".format(msg.author.mention, attachment['filename']))
