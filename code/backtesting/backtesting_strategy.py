import configparser
import logging
import sys
from pathlib import Path  # if you haven't already done so

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.dom.trade import Trade_Action
from trading.strategy import TradingStrategy

logger = logging.getLogger()

class Backtesting_Strategy(TradingStrategy):
    def __init__(self, instrument, pair_file, logger = None, unit_test = False):
        super().__init__(instrument = instrument, pair_file = pair_file, api = None, unit_test = unit_test)

    def determine_trade_action(self, have_units) -> Trade_Action:

        if have_units != 0:  # if already have positions
            logger.debug(f"Have {have_units} positions, checking for stoll loss")
            trade_action = self.check_for_sl(have_units)
            if trade_action is not None:
                return trade_action

            logger.debug(f"Have {have_units} positions, checking if need to close")
            if len (self.trading_session.trades) > 0:
                trade = self.check_if_need_close_trade_from_hist()
            else:
                trade = self.check_if_need_close_trade(have_units)
    
            if trade is not None:
                return trade

        else:        
            logger.debug(f"Have {have_units} positions, checking if need to open")
            
            trade = self.check_if_need_open_trade(have_units)
            if trade is not None:
                return trade

        return None


    def check_if_need_open_trade(self, have_units):
        
        spread = round(self.ask - self.bid, 4)
        # check if need to open a new position
        if spread >= abs(self.bb_upper - self.sma):                            
            logger.debug(f"Current spread: {spread} is too large to trade for possible gain: {round(abs(self.bb_upper - self.sma), 6)}")
            return None

        # if abs(have_units) <= units_to_trade:
        if have_units == 0:
            
            signal = 0

            if self.ask < self.bb_lower and self.has_low_rsi() and self.rsi > self.rsi_min: # if price is below lower BB, BUY
                signal = 1
                logger.info(f"Go Long - BUY at ask price: {self.ask}, rsi: {self.rsi}")
                return Trade_Action(self.instrument, signal * (self.units_to_trade + (0 if have_units == 0 else 1)), self.ask, spread, "Go Long - Buy", True, False)

            elif self.bid > self.bb_upper and self.has_high_rsi and self.rsi < self.rsi_max:  # if price is above upper BB, SELL
                signal = -1
                logger.info(f"Go Short - SELL at bid price: {self.bid}, rsi: {self.rsi}")
                return Trade_Action(self.instrument, signal * (self.units_to_trade + (0 if have_units == 0 else 1)), self.bid, spread, "Go Short - Sell", True, False)
            
        return None

    def has_high_rsi(self):

        for rsi in self.rsi_hist:
            if rsi == self.rsi_max and self.rsi_max > 70:
                return True

        return False

    def has_low_rsi(self):
        
        for rsi in self.rsi_hist:
            if rsi == self.rsi_min and self.rsi_min < 30:
                return True

        return False

