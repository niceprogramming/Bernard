from . import config
from . import common
from . import discord
from . import analytics
from . import database
from . import journal

import time
import logging
import asyncio

logger = logging.getLogger(__name__)
logger.info("loading...")

@discord.bot.command(pass_context=True)
async def sync(ctx, check=None):
    if check is None:
        s = subscriber_update(ctx.message.author)
    else:
        if common.isDiscordAdministrator(ctx.message.author):
            if len(ctx.message.mentions) == 0:
                s = subscriber_update(ctx.message.server.get_member_named(check))
            else:
                s = subscriber_update(ctx.message.mentions[0])
        else:
            s = subscriber_update(ctx.message.author)

    #ask for the data from the provider (destinygg)
    await s.get_provider_data()
    if s.provider_data == None:
        await discord.bot.say("{0.message.author.mention} could not look you up with provider. Check your profile on destiny.gg".format(ctx))
        return

    #get the discord role
    s.get_provider_to_discord_role()
    if s.feature == "pleb":
        await discord.bot.say("{0.message.author.mention} provider returned no active subscription.".format(ctx))
        return

    #if we make it this far get the sub data and lets do something with it
    s.get_provider_subscription_end()
    await s.update_subscriber()

    await discord.bot.say(s.result)

@discord.bot.command(pass_context=True)
async def subaudit(ctx, check=None):
    if common.isDiscordAdministrator(ctx.message.author) is not True:
        return

    if check is None:
        s = subscriber_update(ctx.message.author)
    else:
        if common.isDiscordAdministrator(ctx.message.author):
            if len(ctx.message.mentions) == 0:
                s = subscriber_update(ctx.message.server.get_member_named(check))
            else:
                s = subscriber_update(ctx.message.mentions[0])
        else:
            s = subscriber_update(ctx.message.author)

    await s.audit_subscriber()
    await discord.bot.say(s.result)

class subscriber_update:
    def __init__(self, user):
        self.user = user
        self.today = int(time.strftime('%j', time.time()))

    async def get_provider_data(self):
        self.provider_data = await common.getJSON(config.cfg['subscriber']['provider']['endpoint']+"/?privatekey="+config.cfg['subscriber']['provider']['privatekey']+"&discordid="+self.user.id)

    def get_provider_to_discord_role(self):
        if len(self.provider_data['features']) == 0:
            self.feature = "pleb"
            self.roleid = None
            return

        #work our way from the biggest to smallest, give the highest role we find
        for feature in self.provider_data['features']:
            if feature == config.cfg['subscriber']['features']['tier4']['provided']:
                self.feature = "tier4"
                self.roleid = config.cfg['subscriber']['features']['tier4']['roleid']
                continue
            elif feature == config.cfg['subscriber']['features']['tier3']['provided']:
                self.feature = "tier3"
                self.roleid = config.cfg['subscriber']['features']['tier3']['roleid']
                continue
            elif feature == config.cfg['subscriber']['features']['tier2']['provided']:
                self.feature = "tier2"
                self.roleid = config.cfg['subscriber']['features']['tier2']['roleid']
                continue
            elif feature == config.cfg['subscriber']['features']['tier1']['provided']:
                self.feature = "tier1"
                self.roleid = config.cfg['subscriber']['features']['tier1']['roleid']
                continue
            else:
                self.feature = "pleb"
                self.roleid = None

    def get_provider_subscription_end(self):
        self.expires = time.mktime(time.strptime(self.provider_data['subscription']['end'], config.cfg['subscriber']['provider']['timestamp']))
        self.expires_day = int(time.strftime('%j', time.gmtime(self.expires))) + config.cfg['subscriber']['settings']['grace_days']

    async def update_subscriber(self):
        #check the db to see if this is an update or an insert
        database.dbCursor.execute('SELECT * FROM subscribers WHERE userid=?', (self.user.id,))
        existing = database.dbCursor.fetchone()

        if existing is None:
            database.dbCursor.execute('INSERT INTO subscribers(userid, roleid, tier, last_updated, expires_epoch, expires_day) VALUES(?,?,?,?,?,?)', (self.user.id, self.roleid, self.feature, time.time(), self.expires, self.expires_day))
            logger.info("Adding new subscriber {0} with {1} expires day {2} ".format(self.user.name, self.feature, self.expires_day))
            journal.update_journal_event(module=__name__, event="SUBCRIBER_NEW", userid=self.user.id, contents=self.expires_day)

            self.role = discord.discord.Role(id=self.roleid, server=config.cfg['discord']['server'])
            await discord.bot.add_roles(self.user, self.role)
            self.result = "{0.mention} Subscrption added! {1} with {2} days until revocation.".format(self.user, self.feature, self.expires_day)

            database.dbConn.commit()
            return
        else:
            logger.info("Updating existing subscriber {0}".format(self.user.name))
            #if the new role doesnt match the old one, remove the old role first then add the new one, otherwise same just update DB
            if existing[2] != self.feature:
                logger.info("{0} old role {1} new role {2}".format(self.user.name, existing[2], self.feature))
                #remove the old role
                self.oldrole = discord.discord.Role(id=existing[1], server=config.cfg['discord']['server'])
                await discord.bot.remove_roles(self.user, self.oldrole)

                #turns out if you send them right away theres a race condition and the removed role comes back lol
                await asyncio.sleep(3)

                #add the new role
                self.newrole = discord.discord.Role(id=self.roleid, server=config.cfg['discord']['server'])
                await discord.bot.add_roles(self.user, self.newrole)
                self.result = "{0.mention} Subscrption updated! was {1}, is now {2} with {3} days until revocation.".format(self.user, existing[1], self.feature, self.expires_day)

            #update the db
            self.result = "{0.mention} Nothing has changed. {1} with {2} days until revocation.".format(self.user, self.feature, self.expires_day)
            database.dbCursor.execute('UPDATE subscribers SET roleid=?, tier=?, last_updated=?, expires_epoch=?, expires_day=? WHERE userid=?', (self.roleid, self.feature, time.time(), self.expires, self.expires_day, self.user.id))
            database.dbConn.commit()

    async def audit_subscriber(self):
        self.audit_hasroles = []
        #the API call is what the user should have, the DB is what we think they should have. Anything else is Fake News
        database.dbCursor.execute('SELECT * FROM subscribers WHERE userid=?', (self.user.id,))
        existing = database.dbCursor.fetchone()

        #self.user.roles = list of dicord.Roles
        #run through the roles assigned and build a list
        for role in self.user.roles:
            logger.info("{0.name} has role {1.id} named {1}".format(self.user, role))
            self.audit_hasroles.append(role.id)

        #compare the list of available features with what was found. This prevents acting on Admin/VIP/e-girl roles
        found_roles = set(self.audit_hasroles).intersection(SUBCRIBER_FEATURES)
        self.audit_foundroles = list(found_roles)

        #does not have any roles we do not care about
        if len(self.audit_foundroles) == 0:
            logger.info("{0.name} {0.id} has no roles to act on for features.".format(self.user))
            self.result = "{0.mention} had no assigned roles to act on.".format(self.user)
            return

        #if they have roles but no database entries, all feature roles are removed
        if existing is None:
            logger.info("{0.name} {0.id} has roles but no database entries! removing roles".format(self.user))
            for role in self.audit_foundroles:
                logger.info("{0.name} {0.id} had role {1} removed due to not in DB".format(self.user, role))
                self.removerole = discord.discord.Role(id=role, server=config.cfg['discord']['server'])
                await discord.bot.remove_roles(self.user, self.removerole)
                await asyncio.sleep(3)
                del(self.removerole)
            self.result = "{0.mention} had roles but not database entries! Removed {1} roles from user".format(self.user, len(self.audit_foundroles))
            return

        #the user should only have 1 feature role at most. If they have more we need to clean up/find why
        if len(self.audit_foundroles) == 1:
            #this should return true if the database has the same role as they are assigned in discord
            if existing[1] == self.audit_foundroles[0]:
                logger.info("{0.name} {0.id} has the correct roles.".format(self.user))
                self.result = "{0.mention} has the correct roles assigned 👏".format(self.user)
                return
        else:
            try:
                self.audit_foundroles.remove(existing[1])
            except:
                logger.warn("{0.name} {0.id} had an incorrect role from database and was not in applied list. Something Broke to remove {1}.".format(self.user, existing[1]))

            for role in self.audit_foundroles:
                logger.info("{0.name} {0.id} has an incorrect role! Removing role {1}.".format(self.user, role))
                self.removerole = discord.discord.Role(id=role, server=config.cfg['discord']['server'])
                await discord.bot.remove_roles(self.user, self.removerole)
                await asyncio.sleep(3)
                del(self.removerole)
            self.result = "{0.mention} had incorrect roles assigned! Removed {1} roles from user".format(self.user, len(self.audit_foundroles))
            return

    async def purge_expired(self):
        database.dbCursor.execute('SELECT * FROM subscribers WHERE userid=?', (self.user.id,))
        existing = database.dbCursor.fetchone()

        #dont even care about people not in db
        if existing is None:
            self.result = "{0.mention} does not exist in the database. Nothing to purge.".format(self.user)
            logger.info("{0.name} {0.id} does not exist in the database. Nothing to purge.".format(self.user))
            return

        #if today is over the expires_day, accounts for rounding by giving user another day of grace. Remove from DB only. audit_subscriber() will remove next run
        if self.today > existing[5]:
            database.dbCursor.execute('DELETE FROM subscribers WHERE userid=?', (self.user.id,))
            database.dbConn.commit()
            self.result = "{0.mention} sub expired. Removing DB entry :(".format(self.user)
            logger.info("{0.name} {0.id} sub expired. Removing DB entry :(".format(self.user))

def on_member_remove_purgedb(user):
    database.dbCursor.execute('SELECT * FROM subscribers WHERE userid=?', (user.id,))
    existing = database.dbCursor.fetchone()

    if existing is not None:
        database.dbCursor.execute('DELETE FROM subscribers WHERE userid=?', (user.id,))
        database.dbConn.commit()
        logger.info("{0.name} {0.id} leaving server with a subscription. Removing DB lookup.".format(self.user))
    else:
        logger.info("{0.name} {0.id} leaving server without a Subscrption. Nothing to do.".format(self.user))

def subscriber_feature_roles():
    logger.info("Building list of subscriber role IDs via subscriber_feature_roles()")
    global SUBCRIBER_FEATURES    
    SUBCRIBER_FEATURES = []
    for feature in config.cfg['subscriber']['features']:
        SUBCRIBER_FEATURES.append(config.cfg['subscriber']['features'][feature]['roleid'])

async def updater_background():
    await discord.bot.wait_until_ready()
    if discord.bot_jobs_ready == False:
        logger.info('updater_background is ready to run, but has a timed hodl of {} seconds until first go.'.format(config.cfg['subscriber']['updater_background']['interval']))
        await asyncio.sleep(config.cfg['subscriber']['updater_background']['interval'])

    while not discord.bot.is_closed:
        job_start = analytics.getEventTime()
        logger.info("Starting background task updater_background() - Interval {0}".format(config.cfg['subscriber']['updater_background']['interval']))

        #get the server server object
        server = discord.bot.get_server(config.cfg['discord']['server'])

        for member in list(server.members):
            update_user = subscriber_update(member)

            await update_user.get_provider_data()
            if update_user.provider_data == None:
                continue

            update_user.get_provider_to_discord_role()
            if update_user.roleid == None:
                continue

            update_user.get_provider_subscription_end()
            await update_user.update_subscriber()

        journal.update_journal_job(module=__name__, job="updater_background", start=job_start, result=None)
        logger.info("Sleeping background task updater_background() - Interval {0}".format(config.cfg['subscriber']['updater_background']['interval']))
        await asyncio.sleep(config.cfg['subscriber']['updater_background']['interval'])

async def auditor_background():
    await discord.bot.wait_until_ready()
    if discord.bot_jobs_ready == False:
        logger.info('auditor_background is ready to run, but has a timed hodl of {} seconds until first go.'.format(config.cfg['subscriber']['auditor_background']['interval']))
        await asyncio.sleep(config.cfg['subscriber']['auditor_background']['interval'])

    while not discord.bot.is_closed:
        job_start = analytics.getEventTime()
        logger.info("Starting background task auditor_background() - Interval {0}".format(config.cfg['subscriber']['updater_background']['interval']))

        #get the server server object
        server = discord.bot.get_server(config.cfg['discord']['server'])

        for member in list(server.members):
            update_user = subscriber_update(member)
            await update_user.audit_subscriber()

        journal.update_journal_job(module=__name__, job="auditor_background", start=job_start, result=None)
        logger.info("Sleeping background task auditor_background() - Interval {0}".format(config.cfg['subscriber']['auditor_background']['interval']))
        await asyncio.sleep(config.cfg['subscriber']['auditor_background']['interval'])

async def database_background():
    await discord.bot.wait_until_ready()
    if discord.bot_jobs_ready == False:
        logger.info('database_background is ready to run, but has a timed hodl of {} seconds until first go.'.format(config.cfg['subscriber']['database_background']['interval']))
        await asyncio.sleep(config.cfg['subscriber']['database_background']['interval'])

    while not discord.bot.is_closed:
        job_start = analytics.getEventTime()
        logger.info("Starting background task database_background() - Interval {0}".format(config.cfg['subscriber']['database_background']['interval']))

        #get the server server object
        server = discord.bot.get_server(config.cfg['discord']['server'])

        for member in list(server.members):
            update_user = subscriber_update(member)
            await update_user.purge_expired()

        journal.update_journal_job(module=__name__, job="database_background", start=job_start, result=None)
        logger.info("Sleeping background task database_background() - Interval {0}".format(config.cfg['subscriber']['database_background']['interval']))
        await asyncio.sleep(config.cfg['subscriber']['database_background']['interval'])


if config.cfg['subscriber']['updater_background']['enable']:
    discord.bot.loop.create_task(updater_background())

if config.cfg['subscriber']['auditor_background']['enable']:
    discord.bot.loop.create_task(auditor_background())

if config.cfg['subscriber']['database_background']['enable']:
    discord.bot.loop.create_task(database_background())

subscriber_feature_roles()