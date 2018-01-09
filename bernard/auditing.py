print("%s loading..." % __name__) 

from . import config
from . import common
from . import discord

import re

async def attachments(msg):
    if config.cfg['auditing']['attachments']['enable'] == 0:
        return

    if common.isDiscordAdministrator(msg.author) is True:
        return

    if msg.attachments is False:
        return

    for attachment in msg.attachments:
        exploded = attachment['filename'].split(".")[1:]
        for ext in exploded:
            ext = ext.replace(".","").replace("-","")
            if ext in config.cfg['auditing']['attachments']['restricted']:
                await discord.bot.delete_message(msg)
                await discord.bot.send_message(msg.channel, "{0}, <:pepoG:352533294862172160> that file format is not allowed to be uploaded here. Filename: `{1}`".format(msg.author.mention, attachment['filename']))
                print("{0}: INFO deleting uploaded file: {1}".format(__name__, attachment['filename']))

async def discord_invites(msg):
    #enable the module or not
    if config.cfg['auditing']['invites']['enable'] == 0:
        return

    #ignore admins we dont even care what they do
    if common.isDiscordAdministrator(msg.author) is True:
        return

    #use regex to find discord.gg links in all shapes and sizes, stop if we dont find any
    matched_discord = re.findall('discord.*gg\/([^\s]+)', msg.content.lower())
    if len(matched_discord) == 0:
        return

    #if the config is using the @everyone role
    if config.cfg['auditing']['invites']['highest_role_blocked'] == "everyone":
        if msg.author.top_role.is_everyone == True:
            await discord.bot.delete_message(msg)
            await discord.bot.send_message(msg.channel, "⚠️ {0} Members without a role are unable to post Discord invites.".format(msg.author.mention))
            print("{0}: INFO deleted invite under reason: 'everyone role'".format(__name__))
    elif msg.author.top_role.id == config.cfg['auditing']['invites']['highest_role_blocked']:
            await discord.bot.delete_message(msg)
            await discord.bot.send_message(msg.channel, "⚠️ {0} Your role does not meet the minimum requirements to post Discord invites.".format(msg.author.mention))
            print("{0}: INFO deleted invite under reason: 'underpowered role'".format(__name__))
    else:   
        print("{0}: INFO allowing discord user to post invite link: {1}".format(__name__, matched_discord[0]))