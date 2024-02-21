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
            if self.ask < self.bb_lower and self.has_low_rsi() and self.reverse_momentum(): # if price is below lower BB, BUY
                signal = 1
                logger.info(f"Go Long - BUY at ask price: {self.ask}, rsi: {self.rsi}")
                return Trade_Action(self.instrument, signal * (self.units_to_trade + (0 if have_units == 0 else 1)), self.ask, spread, "Go Long - Buy", True, False)

            # elif self.bid >= self.bb_upper and self.has_high_rsi() and self.price < self.price_max:  # if price is above upper BB, SELL
            elif self.bid >= self.bb_upper and self.has_high_rsi() and self.reverse_momentum():
                signal = -1
                logger.info(f"Go Short - SELL at bid price: {self.bid}, rsi: {self.rsi}")
                return Trade_Action(self.instrument, signal * (self.units_to_trade + (0 if have_units == 0 else 1)), self.bid, spread, "Go Short - Sell", True, False)
            
        return None


    def reverse_momentum(self):
        return self.momentum * self.momentum_prev <= 0

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

    # def pause_trading(self, date_time) -> bool:

    #     logger.debug(f"Date time: {date_time}")
                
    #     if date_time.weekday() == 3 and date_time.hour >= 13 and date_time.hour <= 18:
    #         return True

    #     if date_time.weekday() == 2 and date_time.day < 8 and date_time.hour >= 13 and date_time.hour <= 18:
    #         return True

    #     return False