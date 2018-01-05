print("Importing... %s" % __name__)

from . import config
from . import common
from . import discord
from . import analytics
from . import database

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

    database.dbCursor.execute('''SELECT count(*) FROM crypto''')
    old = database.dbCursor.fetchone()

    await UpdateCoins().update()

    database.dbCursor.execute('''SELECT count(*) FROM crypto''')
    new = database.dbCursor.fetchone()

    await discord.bot.say("Fetched new tickers from providers. {0} new trade pairs added <:pepoWant:352533805438992395>".format(new[0] - old[0]))

@discord.bot.command(pass_context=True, aliases=['c'])
async def crypto(ctx, coin: str, currency="usd", exchange=None):
    if ctx.message.channel.id != "382400958434377728":
        return

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

    #get the price from the correct API
    price, exchange = await c.getprice(lookup)

    await discord.bot.say("**{0}**: {1} ({2})".format(lookup[2].upper(),price,exchange.title()))

@discord.bot.command(pass_context=True, aliases=['mc'])
async def multicrypto(ctx, coin: str, currency="usd"):
    if ctx.message.channel.id != "382400958434377728":
        return

    await discord.bot.send_typing(ctx.message.channel)

    #get the lookups of all coins that can use the trade pair
    c = TickerFetch(coin, currency)
    lookup = await c.multiexchange()

    #nowhere to go but out
    if lookup is None:
        await discord.bot.say("**500: internal shitcoin error.** Attempted price on None.")
        return
    elif len(lookup) == 1:
        await discord.bot.say("**500: internal shitcoin error.** Only 1 coin available for lookup pair. Try !c instead.")
        return
    else:
        pass
    
    #build the string for chat and send it off
    formatted = ""
    for exchange in lookup:
        pri, exch = await c.getprice(exchange)
        if pri is not None:
            formatted += "**{0}**: {1}\n\n".format(exch, pri)
    await discord.bot.say(formatted)

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
        exchange = lookup[1]
        return price, exchange

    def lazylookup(self):
        database.dbCursor.execute('''SELECT * FROM crypto_lazy WHERE alias=?''', (self.ticker,))
        lazy = database.dbCursor.fetchone()
        if lazy is not None:
            self.ticker = lazy[0]

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
            return self.format(ret['price'])
        else:
            return "API Lookup Failed"

    async def bitfinex(self):
        ret = await common.getJSON('https://api.bitfinex.com/v1/pubticker/'+self.ticker+self.currency)
        if ret is not None:
            return self.format(ret['last_price'])
        else:
            return "API Lookup Failed"

    async def gemini(self):
        ret = await common.getJSON('https://api.gemini.com/v1/pubticker/'+self.ticker+self.currency)
        if ret is not None:
            return self.format(ret['last'])
        else:
            return "API Lookup Failed"

    async def poloniex(self):
        ret = await common.getJSON('https://poloniex.com/public?command=returnTicker')
        if ret is not None:
            try:
                return self.format(ret[self.currency.upper().replace("USD","USDT")+"_"+self.ticker.upper()]['last'])
            except KeyError:
                return None
        else:
            return None

    async def bitstamp(self):
        ret = await common.getJSON('https://www.bitstamp.net/api/v2/ticker/'+self.ticker+''+self.currency+'/')
        if ret is not None:
            try:
                return self.format(ret['last'])
            except:
                return None
        else:
            return None       

    async def bittrex(self):
        ret = await common.getJSON('https://bittrex.com/api/v1.1/public/getticker?market='+self.currency.replace("usd","usdt")+'-'+self.ticker)
        if ret is not None:
            try:
                return self.format(ret['result']['Last'])
            except:
                return None
        else:
            return None

    async def binance(self):
        ret = await common.getJSON('https://api.binance.com/api/v1/ticker/24hr?symbol='+self.ticker.upper()+self.currency.upper())
        if ret is not None:
            return self.format(ret['bidPrice'])
        else:
            return None

    async def kraken(self):
        ret = await common.getJSON('https://api.kraken.com/0/public/Ticker?pair='+self.ticker.replace("btc","xbt")+self.currency)
        if ret is not None:
            for ticker, data in ret['result'].items():
                return self.format(data['c'][0])
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
        await self.bitstamp()
        await self.binance()
        await self.kraken()

    async def flush(self):
        database.dbCursor.execute('''DELETE FROM crypto;''')
        database.dbCursor.execute('''INSERT OR IGNORE INTO crypto(priority, exchange, ticker, currency, uniq) VALUES(?,?,?,?,?)''', (7, "poloniex", "btc", "usd", "poloniexbtcusd"))
        database.dbConn.commit()

    async def gdax(self):
        print("%s UPDATING GDAX TICKERS..." % __name__)
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
        print("%s UPDATING GEMINI TICKERS..." % __name__) 
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
        print("%s UPDATING BITFINEX TICKERS..." % __name__)
        ret = await common.getJSON('https://api.bitfinex.com/v1/symbols')
        if ret is not None:
            for ticker in ret:
                unique = "bitfinex" + ticker[:3] + ticker[-3:]
                database.dbCursor.execute('''INSERT OR IGNORE INTO crypto(priority, exchange, ticker, currency, uniq) VALUES(?,?,?,?,?)''', (4, "bitfinex", ticker[:3], ticker[-3:], unique)) #ticker[-3:] curr | ticker[:3] ticker
            database.dbConn.commit()
            return True
        else:
            return None

    async def bittrex(self):
        print("%s UPDATING BITTREX TICKERS..." % __name__)
        ret = await common.getJSON('https://bittrex.com/api/v1.1/public/getmarkets')
        if ret is not None:
            for ticker in ret['result']:
                unique = "bittrex" + ticker['MarketCurrency'].lower() + ticker['BaseCurrency'].lower().replace("usdt","usd")
                database.dbCursor.execute('''INSERT OR IGNORE INTO crypto(priority,exchange, ticker, currency, uniq) VALUES(?,?,?,?,?)''', (5, "bittrex", ticker['MarketCurrency'].lower(), ticker['BaseCurrency'].lower().replace("usdt","usd"), unique)) #ticker['MarketCurrency'] ticker | ticker['BaseCurrency'] currency            database.dbConn.commit()
            return True
        else:
            return None

    async def poloniex(self):
        print("%s UPDATING POLOINEX TICKERS..." % __name__) 
        ret = await common.getJSON('https://poloniex.com/public?command=returnCurrencies')
        if ret is not None:
            for ticker in ret:
                unique = "poloniex" + ticker.replace("USDT","usd").lower() + "btc"
                database.dbCursor.execute('''INSERT OR IGNORE INTO crypto(priority, exchange, ticker, currency, uniq) VALUES(?,?,?,?,?)''', (7, "poloniex", ticker.replace("USDT","usd").lower(), "btc", unique)) # ticker ticker | ticker['symbol'][:3] ticker
            database.dbConn.commit()
            return True
        else:
            return None

    async def bitstamp(self):
        print("%s UPDATING BITSTAMP TICKERS..." % __name__) 
        ret = await common.getJSON('https://www.bitstamp.net/api/v2/trading-pairs-info/')
        if ret is not None:
            for ticker in ret:
                split = ticker['name'].split("/")
                unique = "bitstamp" + split[0].lower() + split[1].lower()
                database.dbCursor.execute('''INSERT OR IGNORE INTO crypto(priority, exchange, ticker, currency, uniq) VALUES(?,?,?,?,?)''', (6, "bitstamp", split[0].lower(), split[1].lower(), unique))
            database.dbConn.commit()
            return True
        else:
            return None

    async def binance(self):
        print("%s UPDATING BINANCE TICKERS..." % __name__) 
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
        print("%s UPDATING KRAKEN TICKERS..." % __name__) 
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