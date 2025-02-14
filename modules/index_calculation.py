import logging
logger = logging.getLogger(__name__)

class IndexCalculator:
    tables = None
    FIRST_REBALANCE_DAY = 42739

    def __init__(self, tables):
        self.tables = tables
    
    def get_latest_rebalance_day(self, day):
        weights = self.tables['weights']
        # return the same day <=
        latest_rebalance_day = weights[weights['Date'] <= day].iloc[-1]['Date']
        logger.debug(f"Latest rebalance day for {day} is {latest_rebalance_day}")
        return latest_rebalance_day

    def get_weight(self, stock, day):
        weights = self.tables['weights']
        weight = weights[weights['Date'] == day][stock].values[0]
        logger.debug(f"Weight of {stock} on {day} is {weight}")
        return weight

    def get_price(self, stock, day):
        stock_prices = self.tables['stock_prices']
        try:
            price_at_day = stock_prices[stock_prices['Date'] == day][stock].values[0]
            logger.debug(f"Price of {stock} on {day} is {price_at_day}")
            return price_at_day
        except IndexError as e:
            logger.error(f"Stock {stock} not found on day {day}")
            raise e

    def no_of_share(self, stock, day):
        tr_day = self.get_latest_rebalance_day(day)
        logger.debug(f"Latest rebalance day for {day} is {tr_day}")
        return self.get_weight(stock, tr_day) / self.get_price(stock, tr_day)
    
    def get_exchange_rate(self, currency, day):
        fx_rates = self.tables['fx_rates']
        if currency == "USD":
            return 1
        logger.debug(f"Getting exchange rate for {currency} on {day}")
        return fx_rates[fx_rates['Date'] == day][currency + "USD"].values[0]
    
    def get_currency(self, stock):
        currency = self.tables['currency']
        # first column is the stock name, second column is the currency
        logger.debug(f"Getting currency for {stock}")
        return currency[currency.iloc[:, 0] == stock].iloc[0, 1]


    def get_prev_day(self, day):
        stock_prices = self.tables['stock_prices']
        # get the closest or equal day
        logger.debug(f"Getting previous day for {day}")
        return stock_prices[stock_prices['Date'] < day].iloc[-1]['Date']

    def calculate_index(self, day):
        """Calculates the index level for all stocks on a given day."""
        if day <= self.FIRST_REBALANCE_DAY:
            logger.debug(f"Day {day} is before the first rebalance day")
            return 100  # Base index level

        prev_day = self.get_prev_day(day)
        if prev_day is None:
            logger.debug(f"Day {day} is the first day")
            return 100  # First valid index level

        index_level_yesterday = self.calculate_index(prev_day)
        top, bottom = 0, 0

        # Loop over all stocks in stock_prices (excluding "Date" column)
        for stock in self.tables['stock_prices'].columns[1:]:
            currency = self.get_currency(stock)

            # Compute today's market value
            num_shares_today = self.no_of_share(stock, day)
            price_today = self.get_price(stock, day)
            fx_today = self.get_exchange_rate(currency, day)

            # Compute yesterday's market value
            num_shares_yesterday = self.no_of_share(stock, prev_day)
            price_yesterday = self.get_price(stock, prev_day)
            fx_yesterday = self.get_exchange_rate(currency, prev_day)

            # Sum over all stocks
            top += num_shares_today * price_today * fx_today
            bottom += num_shares_yesterday * price_yesterday * fx_yesterday

            logger.debug(f"Stock: {stock}, Top: {top}, Bottom: {bottom}")

        # Compute the index level using your formula
        if bottom == 0:  # Avoid division by zero
            logger.error(f"⚠ Error: Market value denominator is zero on {day}")
            raise ValueError(f"⚠ Error: Market value denominator is zero on {day}")

        return index_level_yesterday * (top / bottom)