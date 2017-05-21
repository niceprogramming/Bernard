import discord
import datetime
import configparser
import random
import asyncio
import sqlite3
import datetime
import time
import re
import aiohttp
from urllib.parse import urlparse

"""
Bernard, For Discord.

A mess written by ILiedAboutCake - 2017

TODO:

- Split background tasks into their own files
- Better error handling for sub_connector()
- Built in health checks for background tasks (supervisor/watchdog process)
- Audit subs db vs discord roles
- Background task for pruning "Deleted User" users in banlist
- Command for sub connector to force an update that users can call
- Purge DB info on ban/kick from server for subscribers
- !bernard command that lets users know what this bot does

"""

#load the configuration
config = configparser.ConfigParser()
config.read('bernard.cfg')

#start the SQLite3 connection
dbConnection = sqlite3.connect(config.get("bernard","database"))
db = dbConnection.cursor()

#start the discord client
client = discord.Client()

#load in some variables from the cfg
subFlairs = [e.strip() for e in config.get("flair", "flairs").split(',')]
whitelistUsers = [e.strip() for e in config.get("roles", "Administrator").split(',')]
bannedUploads = [e.strip() for e in config.get("upload-extension-restrict", "filetypes").split(',')]

#setup discord objects we will be calling a lot
auditChannel = discord.Object(id=config.get("bernard","channel"))
destinyTextChannel = discord.Object(id=config.get("destiny-private-text","text"))
destinyTextRole = discord.Role(id=config.get("destiny-private-text","role"), server=config.get("discord","server"))

pepoThinkers = ['221480025025675265', '252869311545212928', '142313171028410368','170367579263729664'] #mouton, cake, rtba, chenners

@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return
    
    #also, fuck replying to servers that are not destiny.gg
    if int(message.server.id) != int(config.get("discord","server")):
        return

    #put the chat message we got in the console 
    print("channel:" + str(message.channel) + " user:" + str(message.author) + " msg: " + message.content)

    #URL filter
    if(int(config.get("restrict-urls","enable"))):
        #regex to find all links then if any in the message inspect the message
        matchedURLs = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.content )
        if matchedURLs is not None:
            for url in matchedURLs:
                parsedURL = urlparse(url)

                #search the DB for flagged sites
                db.execute('SELECT domain, policy FROM restricted_domains WHERE domain=?', (parsedURL.netloc,))
                dbResult = db.fetchone()

                #we find a valid site to flag
                if dbResult is not None:
                    # 0 = delete and notify, 1 = kick, 2 = auto ban
                    if dbResult[1] is 0:
                        await client.delete_message(message)
                        await client.send_message(message.channel, '⚠️ ' + message.author.mention + ' That URL is prohibited here.')
                    elif dbResult[1] is 1:
                        await client.delete_message(message)
                        await client.kick(message.author)
                        await client.send_message(message.channel, '⚠️ ' + message.author.mention + ' That URL is prohibited here. Kicking User...')
                    elif dbResult[1] is 2:
                        await client.delete_message(message)
                        await client.ban(message.author, delete_message_days = 0)
                        await client.send_message(message.channel, '⚠️ ' + message.author.mention + ' That URL is blacklisted with ban instructions. Banning User...')

    #restrict users from uploading certain filetypes
    if message.attachments:
        if int(config.get("upload-extension-restrict","enable")):
            #ignore the basename but break the message into parts based on .
            exploded = message.attachments[0]['filename'].split(".")[1:]
            for ext in exploded:
                ext = ext.replace(".","").replace("-","")
                if ext in bannedUploads:
                    await client.delete_message(message)
                    await client.send_message(message.channel, '⚠️ ' + message.author.mention + ' That file is prohibited here. ' + message.attachments[0]['filename'])

    #only runs if fun mode is enabled
    if(int(config.get("funmode","enable"))):
        #give some memers a pepo, sometimes
        if message.author.id in pepoThinkers:
            if random.randrange(1,int(config.get("funmode","chance"))) == 3:
                await client.add_reaction(message, 'PepoThink:278704638339842048')

        #give polecat a ferret sometimes
        if message.author.id == '83041706965995520':
            if random.randrange(1,int(config.get("funmode","chance"))) == 5:
                await client.add_reaction(message, 'FerretLOL:271856531857735680')

    #split up the command once for easy usage below
    messageArray = message.content.split()
    if len(messageArray) == 0: return

    #check sub status
    if messageArray[0].startswith('!check'):
        if isDiscordAdmin(config, message.author.roles):
            if len(messageArray) == 1:
                member = message.author #set yourself as the member
                messageArray.insert(1, message.author.mention) #makes things work below as the 2nd item in the list = who to reply to in msg
            elif len(messageArray) == 2:
                member = await client.get_user_info(re.sub("\D", "", messageArray[1])) #vaindil says there is a better way to do this, revisit
            else:
                await client.send_message(message.channel, message.author.mention + " what are you trying to do? <:BASEDWATM8:271856531287441410>")
                return
        else:
            member = message.author
            messageArray.insert(1, message.author.mention)

        dggLookupStr = config.get("dgg","endpoint") + "?privatekey="  + config.get("dgg","privatekey") + "&discordname=" + member.name + "%23" + member.discriminator
        async with aiohttp.get(dggLookupStr) as r:
            #if we find a valid user
            if r.status == 200:
                dggProfile = await r.json()
                sub, exp = dggSubFindRole(config, dggProfile)

                #if sub with an expire date
                if sub is not None and exp is not None:
                    await client.send_message(message.channel, messageArray[1] + " is a Tier " + sub + ". Expires: " + exp)

                #if a special use case w/ no expire date (VIP/Broadcaster/Twitch)
                if sub is not None and exp is None:
                    await client.send_message(message.channel, messageArray[1] + ": Has a nonexpiring role: " + sub)

                #plebs
                if sub is None and exp is None:
                    await client.send_message(message.channel, messageArray[1] + " Does not have an active subscription <:DaFeels:271856531572523010>")
            else:
                await client.send_message(message.channel, messageArray[1] + ", That doesn't look like anything to me. (Discord not configured on https://destiny.gg/profile)")

    #---ignore normies, only listen to admin group defined in config or whitelist---
    allowExec = False
    for role in message.author.roles:
        if int(role.id) == int(config.get("roles", "Administrator")):
            allowExec = True

    #black(ed) URL list control
    if messageArray[0].startswith('!blacklist'):
        if messageArray[1] == "check":
            db.execute('SELECT domain, policy FROM restricted_domains WHERE domain=?', (messageArray[2],))
            dbResult = db.fetchone()
            if dbResult is None:
                await client.send_message(message.channel, messageArray[2] + " was not found")
            else:
                await client.send_message(message.channel, messageArray[2] + " Found with policy: " + str(dbResult[1]))
        elif messageArray[1] == "add":
            db.execute("INSERT INTO restricted_domains ('domain', 'policy') VALUES (?,?)", (messageArray[2], messageArray[3]))
            await client.send_message(message.channel, "added " + messageArray[2] + " to blacklist with policy " + messageArray[3])
        elif messageArray[1] == "delete":
            db.execute('DELETE FROM restricted_domains WHERE domain = ? ', (messageArray[2],))
            await client.send_message(message.channel, "deleted " + messageArray[2])
        else:
            await client.send_message(message.channel, "``` usage: !blacklist <function> <url> <policy> \n <function> = check/add/delete \n <url> = root URL without protocol or path \n <policy> = 0 delete, 1 auto-kick, 2 auto-ban \n example: !blackist add blacked.com 0```")

        dbConnection.commit()

    #sometimes we want normie users to have access too
    if message.author.id in whitelistUsers:
        allowExec = True

    #THE MEMES STOP HERE, REAL DANGEROUS COMMANDS BELOW
    if allowExec == False:
        return

@client.event
async def on_message_delete(message):
    if isMainServer(message.server.id):
        if message.attachments:
            fmt = logTimeNow() + ' **Caught Deleted Message!** {0.author.mention} ({0.author}) **Channel:** {0.channel.mention}\n**Message:** `{0.content}` <{0.attachments[0][url]}>'
        else:
            fmt = logTimeNow() + ' **Caught Deleted Message!** {0.author.mention} ({0.author}) **Channel:** {0.channel.mention}\n**Message:** `{0.content}`'
        await client.send_message(auditChannel, fmt.format(message))

@client.event
async def on_member_ban(message): #message = member
    if isMainServer(message.server.id):
        fmt = logTimeNow() + ' **Banned user!** {0.mention} ({0.name}#{0.discriminator})'
        await client.send_message(auditChannel, fmt.format(message))

@client.event
async def on_member_join(message): #message = member
    if isMainServer(message.server.id):
        create = message.created_at.strftime(config.get("bernard","timestamp"))
        fmt = logTimeNow() + ' **New User!** {0.mention} ({0.name}#{0.discriminator}) : **Account Created:** ' + create
        await client.send_message(auditChannel, fmt.format(message))

@client.event
async def on_member_unban(server, message): #message = user
    if isMainServer(server.id):
        fmt = logTimeNow() + ' **Unbanned user!** {0.mention} ({0.name}#{0.discriminator})'
        await client.send_message(auditChannel, fmt.format(message))
        
@client.event
async def on_voice_state_update(before, after): #before, after = Member object
    if int(config.get("destiny-private-text","enable")):
        #we can safely ignore users who are administrators on the server
        for role in before.roles:
            if int(role.id) == int(config.get("roles", "Administrator")):
                return

        #handle ingress joins from nothing (connect to channel)
        if before.voice.voice_channel == None and after.voice.voice_channel.id == config.get("destiny-private-text","voice"):
            await client.send_message(destinyTextChannel, after.mention + " Welcome to Destiny's private room. You can use this chat for exchanging messages directly. Or not that's okay too.")
            await client.add_roles(after, destinyTextRole)
            return

        #handle egress leaves to nothing (disconnect from channel)
        if after.voice.voice_channel == None and before.voice.voice_channel.id == config.get("destiny-private-text","voice"):
            await client.remove_roles(before, destinyTextRole)
            return

        #handle people who are joining or leaving, but not to the channel we want
        if before.voice.voice_channel == None or after.voice.voice_channel == None:
            return

        #handle people hopping from one channel into the private channel
        if after.voice.voice_channel.id == config.get("destiny-private-text","voice"):
            await client.send_message(destinyTextChannel, after.mention + " Welcome to Destiny's private room. You can use this chat for exchanging messages directly. Or not that's okay too.")
            await client.add_roles(after, destinyTextRole)
            return

        #handle people hopping from the destiny channel to somewhere else
        if before.voice.voice_channel.id == config.get("destiny-private-text","voice"):
            await client.remove_roles(before, destinyTextRole)
            return

@client.event
async def on_ready():
    print('Logged in as ' + client.user.name + ' "' + client.user.id + '"') #say we're good
    await client.change_presence(game=discord.Game(name=config.get("bernard","gamestatus"))) #set our playing status

def isDiscordAdmin(config, roles): #send this message.author.roles
    for role in roles:
        if role.id == config.get("roles", "Administrator"): return True 

#UTC logging for audit channel
def logTimeNow():
    return datetime.datetime.utcnow().strftime(config.get("bernard","timestamp"))

#if we are in the main (dgg) server
def isMainServer(id):
    if int(id) == int(config.get("discord","server")): return True 

#convert what dgg sends us to unix epoch, should make this UTC TODO
def dggSubTimeToEpoch(config, timestamp):
    return int(time.mktime(time.strptime(timestamp, config.get("dgg","timestamp"))))

#convert sub roles into something usable, return a tuple of sub, expire
def dggSubFindRole(config, profile):
    #we want to check for these based on the importance of the, since VIP/Notable gives you more power FOR FREE we check them first
    features = profile['features']
    if config.get("flair","vip") in features: return "VIP", None
    if config.get("flair","broadcaster") in features: return "Notable", None
    #plebguard
    if profile['subscription'] is None and config.get("flair","twitch") not in profile['features']: return None, None
    if config.get("flair","twitch") in features and config.get("flair","t1") in features: return "T2", profile['subscription']['end']
    if config.get("flair","t4") in features: return "T4", profile['subscription']['end']
    if config.get("flair","t3") in features: return "T3", profile['subscription']['end']
    if config.get("flair","t2") in features: return "T2", profile['subscription']['end']
    if config.get("flair","t1") in features: return "T1", profile['subscription']['end']
    if config.get("flair","twitch") in features: return "Twitch", None

async def roleAssign(client, validate, member, discordRole, dggUsername, tier, subExpire, cacheResult=[]):
    if validate is True:
        #if we just need to re-validate the cache
        if cacheResult[4] == tier:
            #DB has the same shit, we can reset cache timer
            db.execute('UPDATE subs SET lastcheck = ? WHERE discordID = ? ',(int(time.time()), member.id))

        #up the expire time to now if the sub role has changed
        else:
            db.execute('UPDATE subs SET expire = ? WHERE discordID = ? ',(int(time.time()), member.id))
            await client.send_message(auditChannel, "**Subscription revoking:** " + member.mention + ", **Tier:** " + tier + ", **DGG Nick:** " + dggUsername)

    if validate is False:
        return

    if validate is None:
        #if the user is not in the database they get this
        db.execute("INSERT INTO subs ('discordName', 'discordDiscriminator', 'discordID', 'dggname', 'tier', 'lastcheck', 'expire') VALUES (?,?,?,?,?,?,?)", (member.name, member.discriminator, member.id, dggUsername, tier, int(time.time()), subExpire))
        await client.add_roles(member, discordRole)
        await client.send_message(auditChannel, "**New subscription connected:** " + member.mention + ", **Tier:** " + tier + ", **DGG Nick:** " + dggUsername)

async def sub_connector():
    #set the roles
    t4Role = discord.Role(id=config.get("roles","T4"), server=config.get("discord","server"))
    t3Role = discord.Role(id=config.get("roles","T3"), server=config.get("discord","server"))
    t2Role = discord.Role(id=config.get("roles","T2"), server=config.get("discord","server"))
    t1Role = discord.Role(id=config.get("roles","T1"), server=config.get("discord","server"))
    #await client.add_roles()

    #wait for the client to become ready
    await client.wait_until_ready()

    while not client.is_closed:
        print("Waking up the subscription updater task...")

        #get the server list
        for server in client.servers:
            #make sure we only make changes to destinyGG 
            if int(server.id) == int(config.get("discord","server")):
                #run through the list of users
                for member in list(server.members):
                    ValidateUser = None

                    #check the cache=
                    db.execute('SELECT discordName, discordDiscriminator, discordID, dggname, tier, lastcheck, expire FROM subs WHERE discordID=?', (member.id,))
                    cacheResult = db.fetchone()

                    #see if the cache returned anything, act upon it
                    if cacheResult is not None:

                        #if the sub is expired
                        if int(cacheResult[6] < time.time()):
                            #remove from the DB
                            db.execute('DELETE FROM subs WHERE discordID = ? ', (member.id,))

                            #send the event to remove the sub
                            if cacheResult[4] == "T1":
                                await client.remove_roles(member, t1Role)
                            elif cacheResult[4] == "T2":
                                await client.remove_roles(member, t2Role)
                            elif cacheResult[4] == "T3":
                                await client.remove_roles(member, t3Role)
                            elif cacheResult[4] == "T4":
                                await client.remove_roles(member, t4Role)
                            else:
                                print(member.name, member.discriminator + " Something went wrong removing a role")
                            continue

                        #figure out if we need to re-check the user
                        timeSinceCacheCheck = int(time.time() - cacheResult[5])
                        if timeSinceCacheCheck > int(config.get("subs","cache")):
                            ValidateUser = True
                        else:
                            ValidateUser = False

                    #if we made it this far, we need to query dgg sorry cene :(
                    dggLookupStr = config.get("dgg","endpoint") + "?privatekey="  + config.get("dgg","privatekey") + "&discordname=" + member.name + "%23" + member.discriminator

                    #open a call to dgg
                    async with aiohttp.get(dggLookupStr) as r:

                        #if we find a valid user
                        if r.status == 200:
                            dggProfile = await r.json()

                            #if we find a valid subscription
                            if (dggProfile['subscription']):

                                #get the expire time in time.time()
                                SubExpire = int(time.mktime(time.strptime(dggProfile['subscription']['end'], config.get("dgg","timestamp"))))

                                #handle T1+Twitch subs, which gives you psuedo T2
                                if config.get("flair","twitch") in dggProfile['features'] and config.get("flair","t1") in dggProfile['features']:
                                    await roleAssign(client, ValidateUser, member, t2Role, dggProfile['username'], "T2", SubExpire, cacheResult)

                                #handle normal T1-T4 subs
                                elif [i for i in subFlairs if i in dggProfile['features']]:
                                    #T4 Logic
                                    if config.get("flair","t4") in dggProfile['features']:
                                        await roleAssign(client, ValidateUser, member, t4Role, dggProfile['username'], "T4", SubExpire, cacheResult)
                                    #T3 Logic
                                    elif config.get("flair","t3") in dggProfile['features']:
                                        await roleAssign(client, ValidateUser, member, t3Role, dggProfile['username'], "T3", SubExpire, cacheResult)
                                    #T2 Logic
                                    elif config.get("flair","t2") in dggProfile['features']:
                                        await roleAssign(client, ValidateUser, member, t2Role, dggProfile['username'], "T2", SubExpire, cacheResult)
                                    #T1 Logic
                                    elif config.get("flair","t1") in dggProfile['features']:
                                        await roleAssign(client, ValidateUser, member, t1Role, dggProfile['username'], "T1", SubExpire, cacheResult)
                                    else:
                                        print("WHAT THE FUK")

                    #commit the database changes (if any)
                    dbConnection.commit()

        print("sleeping the subscription updater task...")
        await asyncio.sleep(int(config.get("subs","interval")))

#cleans up the server of users who have not signed into discord in x days (bernard.cfg -> purge)
async def purge_server():
    print("Waking up the purge_server() task...")
    #await the client to start
    await client.wait_until_ready()

    #build the request
    req = config.get("discord","endpoint") + "/guilds/" + config.get("discord","server") + "/prune?days=" + config.get("purge","age")
    head = {'Authorization':'Bot ' + config.get("discord","token")}

    #send the request
    async with aiohttp.post(req, headers=head) as r:
        if r.status == 200:
            resp = await r.json()
            if resp['pruned'] is not 0:
                await client.send_message(auditChannel, logTimeNow() + " **Pruning Server:** removed " + str(resp['pruned']) + " users not seen in " + config.get("purge","age") + " days")

    #go back to bed based on the config
    print("Sleeping the purge_server() task...")
    await asyncio.sleep(int(config.get("purge","interval")))

#cleans up the server invites that users create perma but become underused (bernard.cfg -> invites)
async def purge_invites():
    print("Waking up the purge_invites() task...")
    #await the client to start
    await client.wait_until_ready()

    #build the request for all users
    req = config.get("discord","endpoint") + "/guilds/" + config.get("discord","server") + "/invites"
    head = {'Authorization':'Bot ' + config.get("discord","token")}

    #get the list of invites
    async with aiohttp.get(req, headers=head) as r:
        if r.status == 200:
            resp = await r.json()

            #work with each invite
            for invite in resp:

                #ignore timed ones that discord gets rid of via expire timers
                if int(invite["max_age"]) is not 0:
                    continue

                #convert the timestamps into usable numbers (unix epoch for easy math and brainfuck when you want to tune this in 3 months) Fuck Python time NoTears.
                SubExpire = int(time.mktime(time.strptime(invite['created_at'], config.get("invites","timestamp"))))
                utcnow = datetime.datetime.utcnow()
                inviteAgeInSeconds = (int(utcnow.timestamp()) - SubExpire)
                InviteAgeInDays = (inviteAgeInSeconds / 86400)

                #if it made it minage days
                if InviteAgeInDays > int(config.get("invites","minage")):

                    #if the key has 0 to minuse uses, lets just get rid of it
                    if 0 <= int(invite['uses']) <= int(config.get("invites","minuse")):
                        print("KILLING INVITE: " + invite['code'] + " USED: " + str(invite['uses']) + " CREATED: " + invite['created_at'])
                        await client.send_message(auditChannel, logTimeNow() + " **Pruned Invite:** " + invite['code'] + " **From:** <@" + invite['inviter']['id'] + "> **Uses:** " + str(invite['uses']) + " **Age:** " + str(round(InviteAgeInDays, 1)) + " days old")

                        #sends the kill to discord
                        async with aiohttp.delete(config.get("discord","endpoint") + "/invites/" + invite['code'], headers=head) as r:
                            delresp = await r.json()

                await asyncio.sleep(3)

    #go back to bed based on the config
    print("Sleeping the purge_invites() task...")
    await asyncio.sleep(int(config.get("invites","interval")))

#watchdog
async def supervisor():
    pass

#start the sub connector
if int(config.get("subs","enable")):
    client.loop.create_task(sub_connector())

#start the inactive user purge
if int(config.get("purge","enable")):
    client.loop.create_task(purge_server())

#start the inactive invite purge
if int(config.get("invites","enable")):
    client.loop.create_task(purge_invites())

#start the supervisor
if int(config.get("supervisor","enable")):
    client.loop.create_task(supervisor())

client.run(config.get("discord","token")) #start the BOT