from . import config
from . import common
from . import discord
from . import journal

import asyncio
import aiohttp
import logging

logger = logging.getLogger(__name__)
logger.info("loading...") 

"""
TODO:
- Silence users in text, write to eventS_regulators
- publish events done via bot to #bernard
- public command to query reuglator actions
"""

#function to build the roles list allowed to be punished, this is kinda hacky
async def get_allowed_groups():
    global untouchable_roles
    untouchable_roles = []

    await discord.bot.wait_until_ready()
    await asyncio.sleep(1)

    #get all the roles, and make a list of them
    all_roles = discord.default_server.roles
    for role in all_roles:
        untouchable_roles.append(role.id)

    #remove default role
    untouchable_roles.remove(discord.default_server.default_role.id)

    #remove twitch role
    untouchable_roles.remove(config.cfg['discord']['twitch_managed_role'])

    #remove destinygg subscriber roles
    for feature in config.cfg['subscriber']['features']:
        untouchable_roles.remove(config.cfg['subscriber']['features'][feature]['roleid'])

#this starts get_allowed_groups() at startup, but requires the bot to be ready
discord.bot.loop.create_task(get_allowed_groups())

#use the same check across all commands to see if the regulator is allowed to preform the action based on permission, role, status
def allow_regulation(ctx):
    #has to be a regulator+
    if common.isDiscordRegulator(ctx.message.author) == True:
        pass
    else:
        logger.info("Attempted to call allow_regulation but was rejected for: no permission")        
        return False

    #has to be a mention, not just typing a username
    if len(ctx.message.mentions) == 0:
        logger.info("Attempted to call allow_regulation but was rejected for: no mention")
        return False
    else:
        target = ctx.message.mentions[0]

    #dont let the user try to play themselves
    if target.id == ctx.message.author.id:
        logger.info("Attempted to call allow_regulation but was rejected for: self harm")
        return False

    #if the user is an admin process it bypassing permissions
    if common.isDiscordAdministrator(ctx.message.author) == True:
        return True

    #get the assigned role IDs
    target_roles = []
    for role in target.roles:
        target_roles.append(role.id)

    #convert the lists to sets
    target_set = set(target_roles)
    untouchable_set = set(untouchable_roles)

    #if they intersect, they should not be touched
    allowed_set = untouchable_set.intersection(target_set)
    if len(allowed_set) == 0:
        return True
    else:
        logger.info("Attempted to call allow_regulation but was rejected for: untouchable role")
        return False

    #failsafe to no if my bad logic fails
    logger.info("Attempted to call allow_regulation but was rejected for: failsafe")
    return False


#kick a user from the server, must supply a user mention and string longer than 4 chars to land
@discord.bot.command(pass_context=True, no_pm=True, hidden=True)
async def kick(ctx, target, *, reason):
    if common.isDiscordRegulator(ctx.message.author) != True:
        return

    #ban reason has to have at least a word in it
    if len(reason) < 4:
        await discord.bot.say("⚠️ Kick reason must be longer than 4 characters. `!kick @username reason goes here`")
        return

    if allow_regulation(ctx):
        #return what is happening in the same channel to alert the user, wait 5 seconds and fire the kick command
        await discord.bot.say("✔️ {} is kicking {} with the reason of `{}`.".format(ctx.message.author.mention, ctx.message.mentions[0].mention, reason))
        await asyncio.sleep(5)
        await discord.bot.kick(ctx.message.mentions[0])

        #update the internal bot log, since we cant send kick reasons via this api version #TODO: in rewrite add that
        journal.update_journal_regulator(invoker=ctx.message.author.id, target=ctx.message.mentions[0].id, eventdata=reason, action="KICK_MEMBER", messageid=ctx.message.id)
    else:
        await discord.bot.say("🛑 {} unable to moderate user. Either you failed to tag the user properly or the member is protected from regulators.".format(ctx.message.author.mention))


#kick a user from the server, must supply a user mention and string longer than 4 chars to land
@discord.bot.command(pass_context=True, no_pm=True, hidden=True)
async def ban(ctx, target, *, reason):
    if common.isDiscordRegulator(ctx.message.author) != True:
        return

    #ban reason has to have at least a word in it
    if len(reason) < 10:
        await discord.bot.say("⚠️ ban reason must be longer than 10 characters. `!ban @username reason goes here`")
        return

    if allow_regulation(ctx):
        await discord.bot.say("✔️ {} is **BANNING** {} with the reason of `{}`.".format(ctx.message.author.mention, ctx.message.mentions[0].mention, reason))
        await asyncio.sleep(5)
        res = await common.ban_verbose(ctx.message.mentions[0], reason)
        if res == False:
            await discord.bot.say("❓ Something's fucked! Unable to issue ban to Discord API. Bother cake.")
        else:
            journal.update_journal_regulator(invoker=ctx.message.author.id, target=ctx.message.mentions[0].id, eventdata=reason, action="BAN_MEMBER", messageid=ctx.message.id)
    else:
        await discord.bot.say("🛑 {} unable to moderate user. Either you failed to tag the user properly or the member is protected from regulators.".format(ctx.message.author.mention))

#strip member of rights to talk in voice rooms
@discord.bot.command(pass_context=True, no_pm=True, hidden=True)
async def silence(ctx, target, *, reason):
    if common.isDiscordRegulator(ctx.message.author) != True:
        return

    #ban reason has to have at least a word in it
    if len(reason) < 4:
        await discord.bot.say("⚠️ Silence reason must be longer than 4 characters. `!silence @username reason goes here`")
        return

    if allow_regulation(ctx):
        await discord.bot.server_voice_state(ctx.message.mentions[0], mute=1)
        journal.update_journal_regulator(invoker=ctx.message.author.id, target=ctx.message.mentions[0].id, eventdata=reason, action="VOICE_SILENCE", messageid=ctx.message.id)
    else:
        await discord.bot.say("🛑 {} unable to moderate user. Either you failed to tag the user properly or the member is protected from regulators.".format(ctx.message.author.mention))

#return member rights to talk in voice rooms
@discord.bot.command(pass_context=True, no_pm=True, hidden=True)
async def unsilence(ctx, target, *, reason):
    if common.isDiscordRegulator(ctx.message.author) != True:
        return

    if allow_regulation(ctx):
        await discord.bot.server_voice_state(ctx.message.mentions[0], mute=0)
        journal.update_journal_regulator(invoker=ctx.message.author.id, target=ctx.message.mentions[0].id, eventdata=reason, action="VOICE_UNSILENCE", messageid=ctx.message.id)
    else:
        await discord.bot.say("🛑 {} unable to moderate user. Either you failed to tag the user properly or the member is protected from regulators.".format(ctx.message.author.mention))        