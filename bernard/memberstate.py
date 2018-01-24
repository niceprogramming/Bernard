from . import config
from . import common
from . import discord
from . import analytics
from . import database
from . import invites

import logging

logger = logging.getLogger(__name__)
logger.info("loading...")

ignore_depart = []

#new member to the server. user = discord.User
@discord.bot.event
async def on_member_join(user): 
    msgProcessStart = analytics.getEventTime()
    if common.isDiscordMainServer(user.server.id) is not True:
        return

    #if the user is retroactively banned, handle it and issue the ban
    database.dbCursor.execute('''SELECT * FROM bans_retroactive WHERE id=?''', (user.id,))
    retdb = database.dbCursor.fetchone()
    if retdb is not None:
        ignore_depart.append(user.id)
        await discord.bot.ban(user)
        await discord.bot.send_message(discord.mod_channel(),"{0} **Retroactive Ban:** {1.mention} (Name:`{1.name}#{1.discriminator}` ID:`{1.id}` REASON: `{2}`)".format(common.bernardUTCTimeNow(), user, retdb[2]))
        return

    ##send the message to the admin defined channel
    await discord.bot.send_message(discord.mod_channel(),"{0} **New User:** {1.mention} (Name:`{1.name}#{1.discriminator}` ID:`{1.id}`) **Account Age:** {2}".format(common.bernardUTCTimeNow(), user, common.bernardAccountAgeToFriendly(user)))

    analytics.onMemberProcessTime(msgProcessStart, analytics.getEventTime())

#member leaving the server. user = discord.User
@discord.bot.event
async def on_member_remove(user):
    msgProcessStart = analytics.getEventTime()
    if common.isDiscordMainServer(user.server.id) is not True:
        return
 
    #if the user was banned or removed for another reason dont issue the depart statement
    if user.id in ignore_depart:
        ignore_depart.remove(user.id)
        return

    await discord.bot.send_message(discord.mod_channel(),"{0} **Departing User:** {1.mention} (Name:`{1.name}#{1.discriminator}` ID:`{1.id}`)".format(common.bernardUTCTimeNow(), user))

    #remove any invites from this user
    await invites.on_member_leave_invite_cleanup(user)

    analytics.onMemberProcessTime(msgProcessStart, analytics.getEventTime())

#member getting banned from the server. member = discord.Member
@discord.bot.event
async def on_member_ban(member):
    msgProcessStart = analytics.getEventTime()
    if common.isDiscordMainServer(member.server.id) is not True:
        return

    ignore_depart.append(member.id)
    await discord.bot.send_message(discord.mod_channel(),"{0} **Banned User:** {1.mention} (Name:`{1.name}#{1.discriminator}` ID:`{1.id}`)".format(common.bernardUTCTimeNow(), member))

    #remove any invites from this user
    await invites.on_member_leave_invite_cleanup(member)

    analytics.onMemberProcessTime(msgProcessStart, analytics.getEventTime())

#unban events server = discord.Server, user = discord.User
@discord.bot.event
async def on_member_unban(server, user): 
    msgProcessStart = analytics.getEventTime()
    if common.isDiscordMainServer(server.id) is not True:
        return

    await discord.bot.send_message(discord.mod_channel(),"{0} **Unbanned User:** {1.mention} (Name:`{1.name}#{1.discriminator}` ID:`{1.id}`)".format(common.bernardUTCTimeNow(), user))

    analytics.onMemberProcessTime(msgProcessStart, analytics.getEventTime())

#user object changes. before/after = discord.Member
@discord.bot.event
async def on_member_update(before, after): 
    msgProcessStart = analytics.getEventTime()
    if common.isDiscordMainServer(before.server.id) is not True:
        return

    #handle nickname changes
    if before.nick != after.nick:
        if before.nick is None:
            await discord.bot.send_message(discord.mod_channel(),"{0} **Server Nickname Added:** {1.mention} is now `{1.name}` was `{2.nick}` (Name:`{1.name}#{1.discriminator}` ID:`{1.id}`)".format(common.bernardUTCTimeNow(), after, before))
        elif after.nick is None:
            await discord.bot.send_message(discord.mod_channel(),"{0} **Server Nickname Removed:** {1.mention} is now `{1.name}` was `{2.nick}` (Name:`{1.name}#{1.discriminator}` ID:`{1.id}`)".format(common.bernardUTCTimeNow(), after, before))
        else:
            await discord.bot.send_message(discord.mod_channel(),"{0} **Server Nickname Changed:** {1.mention} is now `{1.nick}` was `{2.nick}` (Name:`{1.name}#{1.discriminator}` ID:`{1.id}`)".format(common.bernardUTCTimeNow(), after, before))

    #handle username changes
    if before.name != after.name:
        await discord.bot.send_message(discord.mod_channel(),"{0} **Discord Username Changed:** {1.mention} is now `{1.name}` was `{2.name}` (Name:`{1.name}#{1.discriminator}` ID:`{1.id}`)".format(common.bernardUTCTimeNow(), after, before))

    analytics.onMemberProcessTime(msgProcessStart, analytics.getEventTime())