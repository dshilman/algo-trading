import logging

from api import OANDA_API
from strategy import TradingStrategy
from trading.api import OANDA_API
from trading.dom.order import Order
from trading.dom.trade import Trade_Action
from trading.dom.trading_session import Trading_Session
from trading.MyTT import RSI

logger = logging.getLogger()

class EUR_USD_Strategy (TradingStrategy):

    def __init__(self, instrument, pair_file, api: OANDA_API = None, unit_test=False):
        super().__init__(instrument, pair_file, api, unit_test)


    def check_if_need_open_trade(self, have_units):
        
        spread = round(self.ask - self.bid, 4)
        # check if need to open a new position
        if 2.5 * spread >= abs(self.bb_upper - self.sma):                            
            logger.debug(f"Current spread: {spread} is too large to trade for possible gain: {round(abs(self.bb_upper - self.sma), 6)}")
            return None

        # if abs(have_units) <= units_to_trade:
        if have_units == 0:
            
            signal = 0

            # if self.ask <= self.bb_lower and self.has_low_rsi() and self.price > self.price_min: # if price is below lower BB, BUY
            if self.ask < self.bb_lower and self.has_low_rsi() and round(self.momentum, 6) * round(self.momentum_prev, 6) <= 0: # if price is below lower BB, BUY
                signal = 1
                logger.info(f"Go Long - BUY at ask price: {self.ask}, rsi: {self.rsi}")
                return Trade_Action(self.instrument, signal * (self.units_to_trade + (0 if have_units == 0 else 1)), self.ask, spread, "Go Long - Buy", True, False)

            # elif self.bid >= self.bb_upper and self.has_high_rsi() and self.price < self.price_max:  # if price is above upper BB, SELL
            elif self.bid >= self.bb_upper and self.has_high_rsi() and round(self.momentum, 6) * round(self.momentum_prev, 6) <= 0:
                signal = -1
                logger.info(f"Go Short - SELL at bid price: {self.bid}, rsi: {self.rsi}")
                return Trade_Action(self.instrument, signal * (self.units_to_trade + (0 if have_units == 0 else 1)), self.bid, spread, "Go Short - Sell", True, False)
            
        return None

    def check_if_need_close_trade(self, have_units):

        spread = round(self.ask - self.bid, 4)

        if have_units > 0: # long position
                # target price to close long position should be higher than the transaction price, whichever is lowest
                # target = min(round(transaction_price + 3 * abs(self.ask - self.bid), 6), self.sma + (self.ask - self.bid))
                # target = round(transaction_price + 3 * abs(self.ask - self.bid), 6)
                target = self.sma + 0 * spread
                if self.bid >= target and round(self.momentum, 6) * round(self.momentum_prev, 6) <= 0:
                    logger.info(f"Close long position - Sell {-have_units} units at bid price: {self.bid}, target: {target}, target: {target}")
                    return Trade_Action(self.instrument, -have_units, self.ask, (self.ask - self.bid), "Close Long - Sell", False, False)

        if have_units < 0: # short position
                # target price to close short position should be lower than the transaction price, whichever is highest
            # target = max(round(transaction_price - 3 * abs(self.ask - self.bid), 6), self.sma - (self.ask - self.bid))
            target = self.sma - 0 * spread
            # target = round(transaction_price - 3 * abs(self.ask - self.bid), 6)
            if self.ask <= target and round(self.momentum, 6) * round(self.momentum_prev, 6) <= 0:
                logger.info(f"Close short position  - Buy {-have_units} units at ask price: {self.ask}, target: {target}, target: {target}")
                return Trade_Action(self.instrument, -have_units, self.bid, (self.ask - self.bid), "Close Short - Buy", False, False)

        return None


    def has_high_rsi(self):

        # return self.rsi > 70 and self.rsi < self.rsi_max
        return self.rsi_max > 72      
        # for rsi in self.rsi_hist:
        #     if rsi > 70 and self.rsi_max > 72:
        #         return True

        # return False

    def has_low_rsi(self):
        
        # return self.rsi < 30 and self.rsi > self.rsi_min
        return self.rsi_min < 28
        # for rsi in self.rsi_hist:
        #     if rsi < 30 and self.rsi_min < 28:
        #         return True

        # return False
