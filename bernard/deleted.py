from . import config
from . import common
from . import discord
from . import analytics
from . import journal

import logging

logger = logging.getLogger(__name__)
logger.info("loading...")

#new member to the server. message = discord.Message
@discord.bot.event
async def on_message_delete(message): 
    msgProcessStart = analytics.getEventTime()
    if common.isDiscordMainServer(message.server.id) is not True:
        return

    if message.attachments and message.content == "":
        msg = "{0.author.mention} (Name:`{0.author}` ID:`{0.author.id}`) in {0.channel.mention} \n Deleted Attachment: `{0.attachments[0][filename]}` \n URL: <{0.attachments[0][url]}>".format(message)
        journal_msg = "Attachment: {0.attachments[0][filename]} Size: {0.attachments[0][size]}".format(message)
    elif message.attachments and message.content != "":
        msg = "{0.author.mention} (Name:`{0.author}` ID:`{0.author.id}`) in {0.channel.mention} \n Message: \"`{0.content}`\" \n\n Deleted Attachment: `{0.attachments[0][filename]}` \n URL: <{0.attachments[0][url]}>".format(message)
        journal_msg = "Text: {0.content} Attachment: {0.attachments[0][filename]} Size: {0.attachments[0][size]}".format(message)
    else:
        msg = "{0.author.mention} (Name:`{0.author}` ID:`{0.author.id}`) in {0.channel.mention} \n Message: \"`{0.content}`\" \n\n".format(message)
        journal_msg = "Text: {0.content}".format(message)

    await discord.bot.send_message(discord.mod_channel(), "{0} **Caught Deleted Message!** {1}".format(common.bernardUTCTimeNow(), msg))

    journal.update_journal_event(module=__name__, event="ON_MESSAGE_DELETE", userid=message.author.id, eventid=message.id, contents=journal_msg)

    analytics.onMessageProcessTime(msgProcessStart, analytics.getEventTime())