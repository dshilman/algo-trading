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

    def check_if_need_open_trade(self, instrument, have_units, bid, ask, units_to_trade):
        
        price = (ask + bid) / 2
        spread = round(ask - bid, 4)
        # check if need to open a new position
        # if spread >= abs(self.bb_upper - self.sma):                            
        #     logger.warning (f"Current spread: {spread} is too large to trade for possible gain: {round(abs(self.bb_upper - self.sma), 6)}")
        #     return None

        # if abs(have_units) <= units_to_trade:
        if have_units == 0:
            
            signal = 0

            if ask < self.bb_lower and self.rsi_min in self.rsi_hist and self.momentum == self.momentum_min: # if price is below lower BB, BUY
                signal = 1
                logger.info(f"Go Long - BUY at ask price: {ask}, rsi: {self.rsi}")
            elif bid > self.bb_upper and self.rsi_max is self.rsi_hist and self.momentum == self.momentum_min:  # if price is above upper BB, SELL
                signal = -1
                logger.info(f"Go Short - SELL at bid price: {bid}, rsi: {self.rsi}")
            
            """
                Trade 1: +1,000 EUR/USD +SL @ 1.05
                Trade 2: +1,000 EUR/USD +SL @ 1.05
                Trade 2 is cancelled because all trades with a SL, TP, or TS must have a unique size
            """
            if signal != 0:
                return Trade_Action(instrument, signal * (units_to_trade + (0 if have_units == 0 else 1)), (ask if signal > 0 else bid), spread, True)
                

        return None


    def check_if_need_close_trade(self, instrument, have_units, bid, ask):

        signal = 0
        price = (ask + bid) / 2
        spread = round(ask - bid, 4)

        if have_units > 0:  # if already have long positions
            if bid > self.sma and self.momentum == self.momentum_min:  # price is above target SMA, SELL
                signal = -1
                logger.info(f"Close long position - Sell {have_units} units at bid price: {bid}, sma: {self.sma}, rsi: {self.rsi}")
        elif have_units < 0:  # if alredy have short positions
            if ask < self.sma and self.momentum == self.momentum_min:  # price is below target SMA, BUY
                signal = 1
                logger.info(f"Close short position  - Buy {have_units} units at ask price: {ask}, sma: {self.sma}, rsi: {self.rsi}")

        """
            Negative sign if front of have_units "-have_units" means close the existing position
        """
        if signal != 0:
            return Trade_Action(instrument, -have_units, (ask if signal > 0 else bid), spread, False)

        return None


