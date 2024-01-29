import configparser
import logging
import sys
from pathlib import Path  # if you haven't already done so

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.trader import Trade_Action
from trading.trader import Strategy

logger = logging.getLogger()

class Backtesting_Strategy(Strategy):
    def __init__(self, instrument, pairs_file):
        super().__init__(instrument, pairs_file)


    def determine_action(self, bid, ask, have_units, units_to_trade) -> Trade_Action:
        
        price = round((bid + ask)/2, 6)
        spread = round(ask - bid, 4)
        instrument = self.instrument

        if have_units != 0:  # if already have positions
            logger.debug(f"Have {have_units} positions, checking if need to close")
            trade = self.check_if_need_close_trade(instrument, have_units, bid, ask, spread)
            if trade is not None:
                return trade

        # check if need to open a new position
        if spread >= abs(self.bb_upper - self.sma):                            
            logger.warning (f"Current spread: {spread} is too large to trade for possible gain: {round(abs(self.bb_upper - self.sma), 6)}")
            return None
                
        logger.debug(f"Have {have_units} positions, checking if need to open")
        trade = self.check_if_need_open_trade(instrument, have_units, bid, ask, spread, units_to_trade)
        if trade is not None:
            return trade

        return None


    def check_if_need_open_trade(self, instrument, have_units, bid, ask, spread, units_to_trade):
        
        price = (bid + ask)/2
        # if abs(have_units) <= units_to_trade:
        if have_units == 0:
            
            signal = 0

            if price < self.bb_lower and self.rsi < 30 and self.rsi > self.rsi_min and self.slope * self.slope_prev < 0: # if price is below lower BB, BUY
                signal = 1
                logger.info(f"Go Long - BUY at price: {ask}, rsi: {self.rsi}")
            elif price > self.bb_upper and self.rsi > 70 and self.rsi < self.rsi_max and self.slope * self.slope_prev < 0:  # if price is above upper BB, SELL
                signal = -1
                logger.info(f"Go Short - SELL at price: {bid}, rsi: {self.rsi}")
            
            """
                Trade 1: +1,000 EUR/USD +SL @ 1.05
                Trade 2: +1,000 EUR/USD +SL @ 1.05
                Trade 2 is cancelled because all trades with a SL, TP, or TS must have a unique size
            """
            if signal != 0:
                return Trade_Action(instrument, signal * (units_to_trade + (0 if have_units == 0 else 1)), (ask if signal == 1 else bid), spread, True)
                

        return None


    def check_if_need_close_trade(self, instrument, have_units, bid, ask, spread):

        signal = 0
        price = (bid + ask)/2

        if have_units > 0:  # if already have long positions
            if price > self.sma and self.rsi < self.rsi_max and self.slope * self.slope_prev < 0:
                signal = -1
                logger.info(f"Close long position - Sell {have_units} units at price: {bid}, sma: {self.sma}, rsi: {self.rsi}")
        elif have_units < 0:  # if alredy have short positions
            if price < self.sma and self.rsi > self.rsi_min and self.slope * self.slope_prev < 0:  # price is below target SMA, BUY
                signal = 1
                logger.info(f"Close short position  - Buy {have_units} units at price: {ask}, sma: {self.sma}, rsi: {self.rsi}")

        """
            Negative sign if front of have_units "-have_units" means close the existing position
        """
        if signal != 0:
            return Trade_Action(instrument, -have_units, (ask if signal == 1 else bid), spread, False)

        return None
