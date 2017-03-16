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
auditChannel = discord.Object(id=config.get("bernard","channel"))

pepoThinkers = ['121406689613185025', '221480025025675265', '252869311545212928', '142313171028410368','170367579263729664'] #micspam, mouton, cake, rtba, chenners

@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return
    
    #also, fuck replying to servers that are not destiny.gg
    if int(message.server.id) != int(config.get("discord","server")):
        return

    #ignore normies, only listen to admin group defined in config or whitelist
    allowExec = False
    for role in message.author.roles:
        if int(role.id) == int(config.get("roles", "Administrator")):
            allowExec = True

    #sometimes we want normie users to have access too
    if message.author.id in whitelistUsers:
        allowExec = True

    #put the chat message we got in the console 
    print("channel:" + str(message.channel) + " user:" + str(message.author) + " msg: " + message.content)

    #give some memers a pepo, sometimes
    if message.author.id in pepoThinkers:
        if random.randrange(1,10) == 3:
            await client.add_reaction(message, 'PepoThink:278704638339842048')

    #give polecat a ferret sometimes
    if message.author.id == '83041706965995520':
        if random.randrange(1,10) == 5:
            await client.add_reaction(message, 'FerretLOL:271856531857735680')

    #THE MEMES STOP HERE, REAL DANGEROUS COMMANDS BELOW
    if allowExec == False:
        return

    #split up the command once for easy usage below
    messageArray = message.content.split()

    #good sanity check if the bot is responding
    if messageArray[0].startswith('!pepo'):
        await client.send_message(message.channel, '<:PepoThink:278704638339842048>')

    if messageArray[0].startswith('!check'):
        #turns the user mention into something we can call dgg with
        member = await client.get_user_info(re.sub("\D", "", messageArray[1]))

        #build the dgg query
        dggLookupStr = config.get("dgg","endpoint") + "?privatekey="  + config.get("dgg","privatekey") + "&discordname=" + member.name + "%23" + member.discriminator

        #open a call to dgg
        async with aiohttp.get(dggLookupStr) as r:

            #if we find a valid user
            if r.status == 200:
                dggProfile = await r.json()

                #if the user sub is valid
                if (dggProfile['subscription']):

                    #handle T1+Twitch subs, which gives you psuedo T2
                    if config.get("flair","twitch") in dggProfile['features'] and config.get("flair","t1") in dggProfile['features']:
                        await client.send_message(message.channel, messageArray[1] + ": Psuedo T2 (T1+Twitch) - Expires " + dggProfile['subscription']['end'])

                    #handle normal T1-T4 subs
                    elif [i for i in subFlairs if i in dggProfile['features']]:

                        #T4 Logic
                        if config.get("flair","t4") in dggProfile['features']:
                            await client.send_message(message.channel, messageArray[1] + ": Found Tier 4 - Expires " + dggProfile['subscription']['end'])
                        #T3 Logic
                        elif config.get("flair","t3") in dggProfile['features']:
                            await client.send_message(message.channel, messageArray[1] + ": Found Tier 3 - Expires " + dggProfile['subscription']['end'])
                        #T2 Logic
                        elif config.get("flair","t2") in dggProfile['features']:
                            await client.send_message(message.channel, messageArray[1] + ": Found Tier 2 - Expires " + dggProfile['subscription']['end'])
                        #T1 Logic
                        elif config.get("flair","t1") in dggProfile['features']:
                            await client.send_message(message.channel, messageArray[1] + ": Found Tier 1 - Expires " + dggProfile['subscription']['end'])
                        else:
                            await client.send_message(message.channel, messageArray[1] + " IDK what the fuck you're trying to do, something went wrong. Bother Cake.")

                #handle if they are only a twitch sub
                elif config.get("flair","twitch") in dggProfile['features']: 
                    await client.send_message(message.channel, messageArray[1] + ": Found Twitch sub connected to Destiny.gg.")

                else:
                    await client.send_message(message.channel, messageArray[1] + " Does not have an active subscription <:DaFeels:271856531572523010>")

            else:
                #not connected
                await client.send_message(message.channel, messageArray[1] + " Does not have their Discord configured on destiny.gg https://destiny.gg/profile <:DaFeels:271856531572523010>")

@client.event
async def on_message_delete(message):
    if isMainServer(message.server.id):
        timestamp = message.timestamp.strftime("%x - %X")
        if message.attachments:
            fmt = '**Time:** ' + timestamp + ' **Caught Deleted Message!** {0.author.mention} ({0.author}) **Channel:** {0.channel.mention}\n**Message:** `{0.content}` `{0.attachments[0][url]}`'
        else:
            fmt = '**Time:** ' + timestamp + ' **Caught Deleted Message!** {0.author.mention} ({0.author}) **Channel:** {0.channel.mention}\n**Message:** `{0.content}`'
        await client.send_message(auditChannel, fmt.format(message))

@client.event
async def on_member_ban(message):
    if isMainServer(message.server.id):
        fmt = '**Time:** **Banned user!** {0.mention}'
        await client.send_message(auditChannel, fmt.format(message))

@client.event
async def on_member_join(message):
    if isMainServer(message.server.id):
        fmt = '**Time:** **New User!** {0.mention}\n'
        await client.send_message(auditChannel, fmt.format(message))

@client.event
async def on_member_unban(server, message):
    if isMainServer(message.server.id):
        fmt = '**Time:** **Unbanned user!** {0.mention}'
        await client.send_message(auditChannel, fmt.format(message))

@client.event
async def on_ready():
    print('Logged in as ' + client.user.name + ' "' + client.user.id + '"') #say we're good
    await client.change_presence(game=discord.Game(name=config.get("bernard","gamestatus"))) #set our playing status

def isMainServer(id):
    if int(id) == int(config.get("discord","server")):
        return True
    else:
        return False

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
            await client.send_message(auditChannel, "**Pruning Server:** removed " + str(resp['pruned']) + " users not seen in " + config.get("purge","age") + " days")

    #go back to bed based on the config
    print("Sleeping the purge_server() task...")
    await asyncio.sleep(int(config.get("purge","interval")))

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

                #if the invite is younger than minage days, lets ignore it
                if InviteAgeInDays < int(config.get("invites","minage")):
                    continue

                #if it made it minage days, but has been used minuse times, lets ignore it
                if InviteAgeInDays > int(config.get("invites","minage")) and int(invite['uses']) >= int(config.get("invites","minuse")):
                    continue

                #if it has made it maxage days, and has been used over maxuse times, lets ignore it
                if InviteAgeInDays > int(config.get("invites","maxage")) and int(invite['uses']) >= int(config.get("invites","maxuse")):
                    continue

                #if we made it this far, the key is sunzo :( lets kill it rip
                print("KILLING INVITE: " + invite['code'] + " USED: " + str(invite['uses']) + " CREATED: " + invite['created_at'])
                await client.send_message(auditChannel, "**Pruned Invite:** " + invite['code'] + " **From:** <@" + invite['inviter']['id'] + "> **Uses:** " + str(invite['uses']) + " **Age:** " + str(round(InviteAgeInDays, 1)) + " days old")

                #send the kill switch :(
                async with aiohttp.delete(config.get("discord","endpoint") + "/invites/" + invite['code'], headers=head) as r:
                    delresp = await r.json()

                await asyncio.sleep(5)

    #go back to bed based on the config
    print("Sleeping the purge_invites() task...")
    await asyncio.sleep(int(config.get("invites","interval")))

#start the sub connector
if int(config.get("subs","enable")):
    client.loop.create_task(sub_connector())

#start the inactive user purge
if int(config.get("purge","enable")):
    client.loop.create_task(purge_server())

#start the inactive invite purge
if int(config.get("invites","enable")):
    client.loop.create_task(purge_invites())

client.run(config.get("discord","token")) #start the BOT