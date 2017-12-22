print("Importing... %s" % __name__)

from . import config
from . import common
from . import discord
from . import analytics
from . import database

import aiohttp


@discord.bot.command(pass_context=True, no_pm=True, aliases=['mc'])
async def multicrypto(ctx, coin: str, currency="usd", exchange=None):
    if ctx.message.channel.id != "382400958434377728":
        return

    c = TickerFetch(coin, currency)
    lookup = await c.multi()
    await discord.bot.say("DBG: {}".format(lookup))

@discord.bot.group(pass_context=True, no_pm=True, hidden=True, aliases=['cadm'])
async def cryptoadmin(ctx):
    if common.isDiscordAdministrator(ctx.message.author.roles) is not True:
        return

@cryptoadmin.command(pass_context=True, no_pm=True, hidden=True)
async def alias(ctx, action: str, ticker=None, alias=None):
    if common.isDiscordAdministrator(ctx.message.author.roles):
        if action == "add":
            database.dbCursor.execute('''INSERT INTO crypto_lazy(ticker, alias, added, issued) VALUES(?,?,?,?)''', (ticker, alias, analytics.getEventTime(), ctx.message.author.name))
            database.dbConn.commit()
            await discord.bot.say("**Alias Added:** `{0}` will use ticker `{1}` in lookup attempts".format(alias, ticker))
        elif action == "remove":
            database.dbCursor.execute('''DELETE FROM crypto_lazy WHERE alias=?''', (alias,))
            database.dbConn.commit()
            await discord.bot.say("**Aliases removed: `{0}`**".format(alias))
        elif action == "info":
            database.dbCursor.execute('''SELECT * FROM crypto_lazy WHERE ticker=? OR alias=?''', (ticker, alias))
            table = database.dbCursor.fetchall()
            for result in table:
                await discord.bot.say("**{0}** using ticker `{1}` added by `{2}`".format(result[1], result[0], result[3]))
        else:
            await discord.bot.say("!cryptoadmin alias <add|remove|info> <ticker> <alias>")

@cryptoadmin.command(pass_context=True, no_pm=True)
async def sync(ctx):
    database.dbCursor.execute('''SELECT count(*) FROM crypto''')
    old = database.dbCursor.fetchone()

    await UpdateCoins().update()

    database.dbCursor.execute('''SELECT count(*) FROM crypto''')
    new = database.dbCursor.fetchone()

    await discord.bot.say("Fetched new tickers from providers. {0} new trade pairs added <:pepoWant:352533805438992395>".format(new[0] - old[0]))

@discord.bot.command(pass_context=True, no_pm=True, aliases=['c'])
async def crypto(ctx, coin: str, currency="usd", exchange=None):
    if ctx.message.channel.id != "382400958434377728":
        return

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

    if lookup[0] == 1:
        price = await c.gdax()
    elif lookup[0] == 2:
        price = await c.gemini()
    elif lookup[0] == 3:
        price = await c.bitfinex()
    elif lookup[0] == 4:
        price = await c.bittrex()
    elif lookup[0] == 5:
        price = await c.poloniex()
    elif lookup[0] == 6:
        price = await c.binance()

    if lookup[3] == "usd":
        await discord.bot.say("**{0}**: ${1} USD ({2})".format(lookup[2].upper(),round(price,2),lookup[1]))
    elif lookup[3] == "btc":
        await discord.bot.say("**{0}**: {1} BTC ({2})".format(lookup[2].upper(),btcformat(price),lookup[1]))
    elif lookup[3] == "eth":
        await discord.bot.say("**{0}**: {1} ETH ({2})".format(lookup[2].upper(),round(price,2),lookup[1]))
    elif lookup[3] == "eur":
        await discord.bot.say("**{0}**: €{1} EUR ({2})".format(lookup[2].upper(),price,lookup[1]))
    else:
        await discord.bot.say("500: internal shitcoin error")
  
def btcformat(btc):
    return format(btc, '.8f')

class Coin:
    def __init__(self, ticker, currency='usd', exchange=None):
        self.ticker = ticker.lower()
        self.exchange = exchange
        self.currency = currency.lower()

    async def multi(self):
        self.price_gdax = await self.gdax()
        self.price_gemini = await self.gemini()
        self.price_bitfinex = await self.bitfinex()
        self.price_poloniex = await self.poloniex()
        self.price_bittrex = await self.bittrex()
        self.price_binance = await self.binance()
        return {"gdax":self.price_gdax,"gemini":self.price_gemini,"bitfinex":self.price_bitfinex,"poloniex":self.price_poloniex,"bittrex":self.price_bittrex,"binance":self.price_binance}

    async def findexchange(self):
        self.lazylookup()
        if self.exchange == None:
            database.dbCursor.execute('''SELECT * FROM crypto WHERE ticker=? AND currency=? ORDER BY priority ASC''', (self.ticker, self.currency))
            return database.dbCursor.fetchone()
        else:
            database.dbCursor.execute('''SELECT * FROM crypto WHERE exchange=? AND ticker=? AND currency=? ORDER BY priority ASC''', (self.exchange, self.ticker, self.currency))
            return database.dbCursor.fetchone()

    def lazylookup(self):
        database.dbCursor.execute('''SELECT * FROM crypto_lazy WHERE alias=?''', (self.ticker,))
        lazy = database.dbCursor.fetchone()
        if lazy is not None:
            self.ticker = lazy[0]

class TickerFetch(Coin):
    async def gdax(self):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.gdax.com/products/'+self.ticker+'-'+self.currency+'/ticker', timeout=2) as r:
                if r.status == 200:
                    ret = await r.json()
                    return float(ret['price'])
                else:
                    return None

    async def bitfinex(self):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.bitfinex.com/v1/pubticker/'+self.ticker+self.currency, timeout=2) as r:
                if r.status == 200:
                    ret = await r.json()
                    return float(ret['last_price'])
                else:
                    return None

    async def gemini(self):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.gemini.com/v1/pubticker/'+self.ticker+self.currency, timeout=2) as r:
                if r.status == 200:
                    ret = await r.json()
                    return float(ret['last'])
                else:
                    return None

    async def poloniex(self):
        async with aiohttp.ClientSession() as session:
            if self.currency == "usd":
                self.currency = "USDT"
            async with session.get('https://poloniex.com/public?command=returnTicker', timeout=2) as r:
                if r.status == 200:
                    ret = await r.json()
                    try:
                        return float(ret[self.currency.upper()+"_"+self.ticker.upper()]['last'])
                    except KeyError:
                        return None
                else:
                    return None

    async def bittrex(self):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://bittrex.com/api/v1.1/public/getticker?market='+self.currency.upper()+'-'+self.ticker.upper(), timeout=2) as r:
                if r.status == 200:
                    ret = await r.json()
                    try:
                        return float(ret['result']['Last'])
                    except:
                        return None
                else:
                    return None

    async def binance(self):
        async with aiohttp.ClientSession() as session:
            if self.currency == "usd":
                self.currency = "USDT"

            async with session.get('https://api.binance.com/api/v1/ticker/24hr?symbol='+self.ticker.upper()+self.currency.upper(), timeout=2) as r:
                if r.status == 200:
                    ret = await r.json()
                    return float(ret['bidPrice'])
                else:
                    return None

class UpdateCoins:
    async def update(self):
        await self.flush()

        await self.gdax()
        await self.gemini()
        await self.bitfinex()
        await self.bittrex()
        await self.poloniex()
        await self.binance()

    async def flush(self):
        database.dbCursor.execute('''DELETE FROM crypto;''')
        database.dbConn.commit()

    async def gdax(self):
        print("%s UPDATING GDAX TICKERS..." % __name__)
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.gdax.com/products') as r:
                if r.status == 200:
                    ret = await r.json()
                    for ticker in ret:
                        # ticker['symbol'][-3:] currency | ticker['symbol'][:3] ticker
                        database.dbCursor.execute('''INSERT INTO crypto(priority, exchange, ticker, currency) VALUES(?,?,?,?)''', (1, "gdax", ticker['base_currency'].lower(), ticker['quote_currency'].lower()))
                    database.dbConn.commit()
                    return True
                else:
                    return None

    async def gemini(self):
        print("%s UPDATING GEMINI TICKERS..." % __name__) 
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.gemini.com/v1/symbols') as r:
                if r.status == 200:
                    ret = await r.json()
                    for ticker in ret:
                        # ticker[-3:] currency | ticker[:3] ticker
                        database.dbCursor.execute('''INSERT INTO crypto(priority, exchange, ticker, currency) VALUES(?,?,?,?)''', (2, "gemini", ticker[:3].lower(), ticker[-3:].lower()))
                    database.dbConn.commit()
                    return True
                else:
                    return None

    async def bitfinex(self):
        print("%s UPDATING BITFINEX TICKERS..." % __name__)
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.bitfinex.com/v1/symbols') as r:
                if r.status == 200:
                    ret = await r.json()
                    for ticker in ret:
                        #ticker[-3:] curr | ticker[:3] ticker
                        database.dbCursor.execute('''INSERT INTO crypto(priority, exchange, ticker, currency) VALUES(?,?,?,?)''', (3, "bitfinex", ticker[:3], ticker[-3:]))
                    database.dbConn.commit()
                    return True
                else:
                    return None

    async def bittrex(self):
        print("%s UPDATING BITTREX TICKERS..." % __name__)
        async with aiohttp.ClientSession() as session:
            async with session.get('https://bittrex.com/api/v1.1/public/getmarkets') as r:
                if r.status == 200:
                    ret = await r.json()
                    for ticker in ret['result']:
                        #ticker['MarketCurrency'] ticker | ticker['BaseCurrency'] currency
                        database.dbCursor.execute('''INSERT INTO crypto(priority,exchange, ticker, currency) VALUES(?,?,?,?)''', (4, "bittrex", ticker['MarketCurrency'].lower(), ticker['BaseCurrency'].lower().replace("usdt","usd")))
                    database.dbConn.commit()
                    return True
                else:
                    return None

    async def poloniex(self):
        print("%s UPDATING POLOINEX TICKERS..." % __name__) 
        async with aiohttp.ClientSession() as session:
            async with session.get('https://poloniex.com/public?command=returnCurrencies') as r:
                if r.status == 200:
                    ret = await r.json()
                    for ticker in ret:
                        # ticker ticker | ticker['symbol'][:3] ticker
                        database.dbCursor.execute('''INSERT INTO crypto(priority, exchange, ticker, currency) VALUES(?,?,?,?)''', (5, "poloniex", ticker.lower(), "btc"))
                    database.dbConn.commit()
                    return True
                else:
                    return None

    async def binance(self):
        print("%s UPDATING BINANCE TICKERS..." % __name__) 
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.binance.com/api/v1/ticker/allPrices') as r:
                if r.status == 200:
                    ret = await r.json()
                    for ticker in ret:
                        # ticker['symbol'][-3:] currency | ticker['symbol'][:3] ticker
                        tick = ticker['symbol'].replace("USDT","usd").lower()
                        database.dbCursor.execute('''INSERT INTO crypto(priority, exchange, ticker, currency) VALUES(?,?,?,?)''', (6, "binance", ticker['symbol'][:3].lower(), tick[-3:]))
                    database.dbConn.commit()
                    return True
                else:
                    return None