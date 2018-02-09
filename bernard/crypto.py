from . import config
from . import common
from . import discord
from . import analytics
from . import database
from . import journal

from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)
logger.info("loading...")

#background job to update coins automatically as set in config.cfg
async def sync_background():
    await discord.bot.wait_until_ready()
    while not discord.bot.is_closed:
        job_start = analytics.getEventTime()
        logger.info("Starting background task sync_background() - Interval {0}".format(config.cfg['chat']['crypto']['background_update_interval']))
        update = UpdateCoins()
        await update.update()
        result = await update.count()
        if update.oldtickers != update.newtickers:
            await discord.bot.send_message(discord.objectFactory(config.cfg['chat']['crypto']['channel']), result)

        journal.update_journal_job(module=__name__, job="sync_background", start=job_start, result="{0} change".format(update.oldtickers - update.newtickers))
        logger.info("Sleeping background task sync_background() - Interval {0}".format(config.cfg['chat']['crypto']['background_update_interval']))
        await asyncio.sleep(config.cfg['chat']['crypto']['background_update_interval'])

if config.cfg['chat']['crypto']['background_update_enable']:
    discord.bot.loop.create_task(sync_background())

@discord.bot.group(pass_context=True, no_pm=True, hidden=True, aliases=['cadm'])
async def cryptoadmin(ctx):
    if common.isDiscordAdministrator(ctx.message.author) is not True:
        return

@cryptoadmin.command(pass_context=True, no_pm=True, hidden=True)
async def alias(ctx, action: str, ticker=None, alias=None):
    if common.isDiscordAdministrator(ctx.message.author):
        if action == "add":
            database.dbCursor.execute('''INSERT OR IGNORE INTO crypto_lazy(ticker, alias, added, issued) VALUES(?,?,?,?)''', (ticker.lower(), alias.lower(), analytics.getEventTime(), ctx.message.author.name))
            database.dbConn.commit()
            await discord.bot.say("**Alias Added:** `{0}` will use ticker `{1}` in lookup attempts".format(alias, ticker))
        elif action == "remove":
            database.dbCursor.execute('''DELETE FROM crypto_lazy WHERE alias=? AND ticker=?''', (alias.lower(), ticker.lower()))
            database.dbConn.commit()
            await discord.bot.say("**Aliases removed:** `{0}` no longer uses ticker `{1}` ".format(alias.lower(), ticker.lower()))
        elif action == "info":
            database.dbCursor.execute('''SELECT * FROM crypto_lazy WHERE ticker=? OR alias=?''', (ticker, alias))
            table = database.dbCursor.fetchall()
            ret = "Ticker/Alias Pairs: **{0}**\n\n".format(ticker.upper())
            for result in table:
                ret += "**{0}** using ticker `{1}` added by `{2}`\n".format(result[1], result[0], result[3])
            await discord.bot.say(ret)
        else:
            await discord.bot.say("!cryptoadmin alias <add|remove|info> <ticker> <alias>")

@cryptoadmin.command(pass_context=True, no_pm=True)
async def sync(ctx):
    if common.isDiscordAdministrator(ctx.message.author) is not True:
        return

    await discord.bot.send_typing(ctx.message.channel)

    updater = UpdateCoins()
    await updater.update()
    result = await updater.count()

    await discord.bot.say(result)

@discord.bot.command(pass_context=True, aliases=['c'])
async def crypto(ctx, coin: str, currency="usd", exchange=None):
    await discord.bot.send_typing(ctx.message.channel)

    #init the Coin class with the ticker and currency
    c = TickerFetch(coin, currency, exchange)

    #figure out what exchanges we can use
    lookup = await c.findexchange()

    if lookup is None:
        #attempt to do a btc lookup as a last resort
        del c
        c = TickerFetch(coin, "btc", exchange)
        lookup = await c.findexchange()
        if lookup is None:
            await discord.bot.say("404: shitcoin lookup not found :(")
            return

    #if the data we have is somehow useless
    if lookup[1] == None:
        await discord.bot.say("**500: internal shitcoin error.** Attempted price on None. VALUES: {0}".format(lookup))
        return

    #get the price from the correct API
    price, exchange = await c.getprice(lookup)

    #if an API is fucking up and returning None just leave
    if price is None:
        await discord.bot.say("**500: internal shitcoin error.** Library returned None.")
        return

    if c.currency == "usd":
        await discord.bot.say("**{0}**: {1} ({2})".format(lookup[2].upper(),price,exchange.title()))
    else:
        usdrough = await c.force_fiat()        
        await discord.bot.say("**{0}**: {1} ({2}) {3}".format(lookup[2].upper(),price,exchange.title(),usdrough))

@discord.bot.command(pass_context=True, aliases=['mc'])
async def multicrypto(ctx, coin: str, currency="usd"):
    await discord.bot.send_typing(ctx.message.channel)

    #get the lookups of all coins that can use the trade pair
    c = TickerFetch(coin, currency)
    lookup = await c.multiexchange()

    #if the first lookup falls flat on its face try btc like !c
    if len(lookup) <= 1:
        del c
        c = TickerFetch(coin, "btc")
        lookup = await c.multiexchange()
        logger.info("multicoin function falling back to BTC: Values {0}".format(len(lookup)))

    #nowhere to go but out
    if len(lookup) == 0:
        await discord.bot.say("**500: Internal Shitcoin Error.** Attempted price on None.")
        return
    elif len(lookup) == 1:
        await discord.bot.say("**500: Internal Shitcoin Error.** Only 1 coin available for lookup pair. Try !c instead.")
        return
    else:
        pass
    
    #build the string for chat and send it off
    formatted = ""
    for exchange in lookup:
        pri, exch = await c.getprice(exchange)
        if pri is not None:
            if c.currency == "usd":
                formatted += "**{0}**: {1}\n\n".format(exch, pri)
            else:
                usdrough = await c.force_fiat()
                formatted += "**{0}**: {1} {2}\n\n".format(exch, pri, usdrough) 
    await discord.bot.say(formatted)

@discord.bot.command(pass_context=True, aliases=['cmc'])
async def coinmarketcap(ctx, coin: str):
    await discord.bot.send_typing(ctx.message.channel)

    c = Coin(coin, "btc")
    cmc = c.cmc_lookup()

    if cmc is None:
        await discord.bot.say("404: shitcoin lookup not found :(")
        return

    ret = await common.getJSON('https://api.coinmarketcap.com/v1/ticker/'+cmc+'/')
    cmc = ret[0]

    emd = discord.embeds.Embed(title='Coin Market Cap data for: {0} "{1}"'.format(coin.upper(), cmc['name']), url="https://coinmarketcap.com/currencies/"+cmc['id']+"/", colour=0xE79015)
    emd.set_thumbnail(url='https://files.coinmarketcap.com/static/img/coins/128x128/'+cmc['id']+'.png')
    emd.add_field(name="Rank", value=cmc['rank'], inline=True)
    emd.add_field(name="Market Cap", value="${:0,.2f}".format(float(cmc['market_cap_usd'])), inline=True)     
    emd.add_field(name="Price (USD)", value="${:,.2f}".format(float(cmc['price_usd'])), inline=True)    
    emd.add_field(name="Price (BTC)", value="{:.8f}".format(float(cmc['price_btc'])), inline=True)
    emd.add_field(name="Available Supply", value="{:,}".format(float(cmc['available_supply'])), inline=True) 
    try:
        emd.add_field(name="Max Supply", value="{:,}".format(float(cmc['max_supply'])), inline=True)
    except TypeError:
        emd.add_field(name="Max Supply", value="∞", inline=True)
    emd.add_field(name="Market Change (1H / 24H / 7D)", value="{}% / {}% / {}%".format(cmc['percent_change_1h'], cmc['percent_change_24h'], cmc['percent_change_7d']), inline=False) 
    emd.set_footer(text="Last Updated: {} EST".format(datetime.fromtimestamp(int(cmc['last_updated'])).isoformat()))

    await discord.bot.say(embed=emd)

@discord.bot.command(pass_context=True, aliases=['cweb'])
async def cryptoweb(ctx):
    await discord.bot.say("Track your favorite coins without shitting up the bot! https://polecat.me/crypto")

@discord.bot.command(pass_context=True, aliases=['csellout'])
async def cakesellout(ctx):
    await discord.bot.say("✡ 🇮🇱 https://www.binance.com/?ref=12222765 🇮🇱 ✡")

class Coin:
    def __init__(self, ticker, currency='usd', exchange=None):
        self.ticker = ticker.lower()
        self.exchange = exchange
        self.currency = currency.lower()
        self.valued = None
        self.fiat_cache = None

    async def multiexchange(self):
        self.lazylookup()
        database.dbCursor.execute('''SELECT * FROM crypto WHERE ticker=? AND currency=? ORDER BY priority ASC''', (self.ticker, self.currency))
        return database.dbCursor.fetchall()

    async def findexchange(self):
        self.lazylookup()
        if self.exchange == None:
            database.dbCursor.execute('''SELECT * FROM crypto WHERE ticker=? AND currency=? ORDER BY priority ASC''', (self.ticker, self.currency))
            return database.dbCursor.fetchone()
        else:
            database.dbCursor.execute('''SELECT * FROM crypto WHERE exchange=? AND ticker=? AND currency=? ORDER BY priority ASC''', (self.exchange, self.ticker, self.currency))
            return database.dbCursor.fetchone()

    def cmc_lookup(self):
        self.lazylookup()
        database.dbCursor.execute('''SELECT * FROM crypto_cmc WHERE ticker=?''', (self.ticker.upper(),))
        retdb = database.dbCursor.fetchone()
        if retdb is None:
            return None
        else:
            return retdb[1] #return ID

    async def force_fiat(self):
        if self.fiat_cache == None:
            if self.currency == "btc":
                ret = await common.getJSON('https://api.gdax.com/products/btc-usd/ticker')
            elif self.currency == "eth":
                ret = await common.getJSON('https://api.gdax.com/products/eth-usd/ticker')
            else:
                logger.warn("cannot force fiat price on currency when it's {0}".format(self.currency))
                return None

            self.fiat_cache = float(ret['price'])

        if self.valued is None:
            return "N/A"
        else:
            form = (self.fiat_cache*float(self.valued))
            return "~${:,.2f} USD".format(float(form))

    async def getprice(self, lookup):
        if lookup[1] == "gdax":
            price = await self.gdax()
        elif lookup[1] == "gemini":
            price = await self.gemini()
        elif lookup[1] == "bitfinex":
            price = await self.bitfinex()
        elif lookup[1] == "bittrex":
            price = await self.bittrex()
        elif lookup[1] == "bitstamp":
            price = await self.bitstamp()
        elif lookup[1] == "binance":
            price = await self.binance()
        elif lookup[1] == "poloniex":
            price = await self.poloniex()
        elif lookup[1] == "kraken":
            price = await self.kraken()
        elif lookup[1] == "kucoin":
            price = await self.kucoin()
        elif lookup[1] ==  "coinmarketcap":
            price = await self.coinmarketcap()
        exchange = lookup[1]
        return price, exchange

    def lazylookup(self):
        database.dbCursor.execute('''SELECT * FROM crypto_lazy WHERE alias=?''', (self.ticker,))
        lazy = database.dbCursor.fetchone()
        if lazy is not None:
            self.ticker = lazy[0]
        else:
            database.dbCursor.execute('''SELECT * FROM crypto_cmc WHERE id=?''', (self.ticker,))
            lazy_fallback = database.dbCursor.fetchone()
            if lazy_fallback is not None:
                self.ticker = lazy_fallback[0].lower()

    def format(self, raw):
        if raw is None:
            return "ERR: NONE"

        if self.currency == "usd" or self.currency == "USDT":
            return "${:,.2f} USD".format(float(raw))
        elif self.currency == "btc":
            return "{:.8f} BTC".format(float(raw))
        elif self.currency == "eth":
            return "{:.8f} ETH".format(float(raw))
        elif self.currency == "eur":
            return "€{:,.2f} EUR".format(float(raw))
        else:
            return "ERR: UNKNOWN CURRRENCY in Coin.format(self, raw)"

class TickerFetch(Coin):
    async def gdax(self):
        ret = await common.getJSON('https://api.gdax.com/products/'+self.ticker+'-'+self.currency+'/ticker')
        if ret is not None:
            self.valued = ret['price']
            return self.format(ret['price'])
        else:
            return "API Lookup Failed"

    async def bitfinex(self):
        ret = await common.getJSON('https://api.bitfinex.com/v1/pubticker/'+self.ticker+self.currency)
        if ret is not None:
            self.valued = ret['last_price']
            return self.format(ret['last_price'])
        else:
            return "API Lookup Failed"

    async def gemini(self):
        ret = await common.getJSON('https://api.gemini.com/v1/pubticker/'+self.ticker+self.currency)
        if ret is not None:
            self.valued = ret['last']
            return self.format(ret['last'])
        else:
            return "API Lookup Failed"

    async def poloniex(self):
        ret = await common.getJSON('https://poloniex.com/public?command=returnTicker')
        if ret is not None:
            try:
                poloniex_api_sucks = ret[self.currency.upper().replace("USD","USDT")+"_"+self.ticker.upper()]['last']
                self.valued = poloniex_api_sucks
                return self.format(poloniex_api_sucks)
            except KeyError:
                return None
        else:
            return None

    async def bitstamp(self):
        ret = await common.getJSON('https://www.bitstamp.net/api/v2/ticker/'+self.ticker+''+self.currency+'/')
        if ret is not None:
            try:
                self.valued = ret['last']
                return self.format(ret['last'])
            except:
                return None
        else:
            return None       

    async def bittrex(self):
        ret = await common.getJSON('https://bittrex.com/api/v1.1/public/getticker?market='+self.currency.replace("usd","usdt")+'-'+self.ticker)
        if ret is not None:
            try:
                self.valued = ret['result']['Last']
                return self.format(ret['result']['Last'])
            except:
                return None
        else:
            return None

    async def binance(self):
        ret = await common.getJSON('https://api.binance.com/api/v1/ticker/24hr?symbol='+self.ticker.upper()+self.currency.replace("usd","usdt").upper())
        if ret is not None:
            self.valued = ret['bidPrice']
            return self.format(ret['bidPrice'])
        else:
            return None

    async def kraken(self):
        ret = await common.getJSON('https://api.kraken.com/0/public/Ticker?pair='+self.ticker.replace("btc","xbt")+self.currency.replace("btc","xbt"))
        if ret is not None:
            try:
                for ticker, data in ret['result'].items():
                    self.valued = data['c'][0]
                    return self.format(data['c'][0])
            except KeyError:
                return None
        else:
            return None

    async def kucoin(self):
        ret = await common.getJSON('https://api.kucoin.com/v1/open/tick?symbol='+self.ticker+'-'+self.currency.replace("usd","usdt"))
        if ret is not None:
            self.valued = ret['data']['lastDealPrice']
            return self.format(ret['data']['lastDealPrice'])
        else:
            return None

    async def coinmarketcap(self):
        cmc = self.cmc_lookup()
        ret = await common.getJSON('https://api.coinmarketcap.com/v1/ticker/'+cmc+'/')

        if ret is not None:
            self.valued = ret[0]['price_btc']
            return self.format(ret[0]['price_btc'])
        else:
            return None

class UpdateCoins:
    def __init__(self):
        self.oldtickers = 0
        self.newtickers = 0

    async def update(self):
        await self.flush()

        await self.gdax()
        await self.gemini()
        await self.bitfinex()
        await self.bittrex()
        await self.poloniex()
        await self.bitstamp()
        await self.binance()
        await self.kraken()
        await self.kucoin()
        await self.coinmarketcap()

    async def flush(self):
        #get how many objects were in DB
        database.dbCursor.execute('''SELECT count(*) FROM crypto''')
        old = database.dbCursor.fetchone()
        self.oldtickers = old[0]

        database.dbCursor.execute('''DELETE FROM crypto;''')
        database.dbCursor.execute('''DELETE FROM crypto_cmc;''')
        database.dbConn.commit()

    async def count(self):
        database.dbCursor.execute('''SELECT count(*) FROM crypto''')
        new = database.dbCursor.fetchone()
        self.newtickers = new[0]

        change = self.newtickers - self.oldtickers

        return "<:pepoWant:352533805438992395> Database updated! Change: {0:,d}. ({1:,d} lookup attempts available)".format(change, self.newtickers)

    async def gdax(self):
        logger.info("UPDATING GDAX TICKERS...")
        ret = await common.getJSON('https://api.gdax.com/products')
        if ret is not None:
            for ticker in ret:
                unique = "gdax" + ticker['base_currency'].lower() + ticker['quote_currency'].lower()
                database.dbCursor.execute('''INSERT OR IGNORE INTO crypto(priority, exchange, ticker, currency, uniq) VALUES(?,?,?,?,?)''', (1, "gdax", ticker['base_currency'].lower(), ticker['quote_currency'].lower(), unique)) # ticker['symbol'][-3:] currency | ticker['symbol'][:3] ticker
            database.dbConn.commit()
            return True
        else:
            return None

    async def gemini(self):
        logger.info("UPDATING GEMINI TICKERS...")
        ret = await common.getJSON('https://api.gemini.com/v1/symbols')
        if ret is not None:
            for ticker in ret:
                unique =  "gemini" + ticker[:3].lower() + ticker[-3:].lower()
                database.dbCursor.execute('''INSERT OR IGNORE INTO crypto(priority, exchange, ticker, currency, uniq) VALUES(?,?,?,?,?)''', (2, "gemini", ticker[:3].lower(), ticker[-3:].lower(), unique)) # ticker[-3:] currency | ticker[:3] ticker
            database.dbConn.commit()
            return True
        else:
            return None

    async def bitfinex(self):
        logger.info("UPDATING BITFINEX TICKERS...")
        ret = await common.getJSON('https://api.bitfinex.com/v1/symbols')
        if ret is not None:
            for ticker in ret:
                unique = "bitfinex" + ticker[:3] + ticker[-3:]
                database.dbCursor.execute('''INSERT OR IGNORE INTO crypto(priority, exchange, ticker, currency, uniq) VALUES(?,?,?,?,?)''', (5, "bitfinex", ticker[:3], ticker[-3:], unique)) #ticker[-3:] curr | ticker[:3] ticker
            database.dbConn.commit()
            return True
        else:
            return None

    async def bittrex(self):
        logger.info("UPDATING BITTREX TICKERS...")
        ret = await common.getJSON('https://bittrex.com/api/v1.1/public/getmarkets')
        if ret is not None:
            for ticker in ret['result']:
                unique = "bittrex" + ticker['MarketCurrency'].lower() + ticker['BaseCurrency'].lower().replace("usdt","usd")
                database.dbCursor.execute('''INSERT OR IGNORE INTO crypto(priority,exchange, ticker, currency, uniq) VALUES(?,?,?,?,?)''', (6, "bittrex", ticker['MarketCurrency'].lower(), ticker['BaseCurrency'].lower().replace("usdt","usd"), unique)) #ticker['MarketCurrency'] ticker | ticker['BaseCurrency'] currency            database.dbConn.commit()
            return True
        else:
            return None

    async def poloniex(self):
        logger.info("UPDATING POLOINEX TICKERS...") 
        database.dbCursor.execute('''INSERT OR IGNORE INTO crypto(priority, exchange, ticker, currency, uniq) VALUES(?,?,?,?,?)''', (8, "poloniex", "btc", "usd", "poloniexbtcusd"))        
        ret = await common.getJSON('https://poloniex.com/public?command=returnCurrencies')
        if ret is not None:
            for ticker in ret:
                unique = "poloniex" + ticker.replace("USDT","usd").lower() + "btc"
                database.dbCursor.execute('''INSERT OR IGNORE INTO crypto(priority, exchange, ticker, currency, uniq) VALUES(?,?,?,?,?)''', (8, "poloniex", ticker.replace("USDT","usd").lower(), "btc", unique)) # ticker ticker | ticker['symbol'][:3] ticker
            database.dbConn.commit()
            return True
        else:
            return None

    async def bitstamp(self):
        logger.info("UPDATING BITSTAMP TICKERS...") 
        ret = await common.getJSON('https://www.bitstamp.net/api/v2/trading-pairs-info/')
        if ret is not None:
            for ticker in ret:
                split = ticker['name'].split("/")
                unique = "bitstamp" + split[0].lower() + split[1].lower()
                database.dbCursor.execute('''INSERT OR IGNORE INTO crypto(priority, exchange, ticker, currency, uniq) VALUES(?,?,?,?,?)''', (7, "bitstamp", split[0].lower(), split[1].lower(), unique))
            database.dbConn.commit()
            return True
        else:
            return None

    async def binance(self):
        logger.info("UPDATING BINANCE TICKERS...") 
        ret = await common.getJSON('https://api.binance.com/api/v1/ticker/allPrices')
        if ret is not None:
            for ticker in ret:
                tick = ticker['symbol'].replace("USDT","usd").lower()
                unique = "binance" + ticker['symbol'][:3].lower() + tick[-3:]
                database.dbCursor.execute('''INSERT OR IGNORE INTO crypto(priority, exchange, ticker, currency, uniq) VALUES(?,?,?,?,?)''', (3, "binance", ticker['symbol'][:3].lower(), tick[-3:], unique)) # ticker['symbol'][-3:] currency | ticker['symbol'][:3] ticker
            database.dbConn.commit()
            return True
        else:
            return None

    async def kraken(self):
        logger.info("UPDATING KRAKEN TICKERS...") 
        ret = await common.getJSON('https://api.kraken.com/0/public/AssetPairs')
        if ret is not None:
            for ticker, data in ret['result'].items():
                d = data['altname'].replace(".d","").replace("XBT","btc").lower()
                unique = "kraken" + d[:3] + d[-3:]
                database.dbCursor.execute('''INSERT OR IGNORE INTO crypto(priority, exchange, ticker, currency, uniq) VALUES(?,?,?,?,?)''', (8, "kraken", d[:3], d[-3:], unique))
            database.dbConn.commit()
            return True
        else:
            return None

    async def kucoin(self):
        logger.info("UPDATING KUCOIN TICKERS...")
        ret = await common.getJSON('https://api.kucoin.com/v1/market/open/symbols')
        if ret is not None:
            for ticker in ret['data']:
                unique = "kucoin" + ticker['coinType'].lower() + ticker['coinTypePair'].lower().replace("usdt","usd")
                database.dbCursor.execute('''INSERT OR IGNORE INTO crypto(priority, exchange, ticker, currency, uniq) VALUES(?,?,?,?,?)''', (4, "kucoin", ticker['coinType'].lower(), ticker['coinTypePair'].lower().replace("usdt","usd"), unique))
            database.dbConn.commit()
            return True
        else:
            return None

    async def coinmarketcap(self):
        logger.info("UPDATING CMC TICKERS AND LOOKUP TABLE...") 
        ret = await common.getJSON('https://api.coinmarketcap.com/v1/ticker/?limit='+str(config.cfg['chat']['crypto']['cmc_limit']))
        if ret is not None:
            for ticker in ret:
                #handle the normal !c / !mc lookups
                unique = "coinmarketcap" + ticker['symbol'] + "btc"
                database.dbCursor.execute('''INSERT OR IGNORE INTO crypto(priority, exchange, ticker, currency, uniq) VALUES(?,?,?,?,?)''', (999, "coinmarketcap", ticker['symbol'].lower(), "btc", unique))
                
                #handle !cmc lookups with the crypto_cmc table
                database.dbCursor.execute('''INSERT OR IGNORE INTO crypto_cmc(ticker, id, name) VALUES(?,?,?)''', (ticker['symbol'], ticker['id'], ticker['name']))
            database.dbConn.commit()
            return True
        else:
            return None
