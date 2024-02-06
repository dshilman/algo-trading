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
        super().__init__(instrument = instrument, pair_file = pair_file, api = None, logger = logger, unit_test = unit_test)


    # def check_if_need_close_trade(self, have_units):
        
    #     trade =  self.check_if_need_close_trade_new()
        
    #     if not trade == None:
    #         return trade

    #     # trade = super().check_if_need_close_trade(have_units)

    #     # if not trade == None:
    #     #     return trade
       
    #     trade = self.check_for_sl()
    #     if not trade == None:
    #         return trade

    #     return None

    
    # def check_if_need_close_trade_new(self):

    #     if len (self.trading_session.trades) > 0:
    #         transaction_price =  self.trading_session.trades[-1][3]
    #         traded_units = self.trading_session.trades[-1][2]

    #         if traded_units > 0:
    #             target = max(transaction_price - 4 * abs(self.ask - self.bid), self.sma)
    #             if self.bid > target and (round(self.momentum, 6) == 0 or self.momentum * self.momentum_prev <= 0):
    #                 self.log_info(f"Close long position - Sell {-traded_units} units at bid price: {self.bid}, sma: {self.sma}, rsi: {self.rsi}")
    #                 return Trade_Action(self.instrument, -traded_units, self.ask, (self.ask - self.bid), False)

    #         if traded_units < 0:
    #             target = min(transaction_price + 4 * abs(self.ask - self.bid), self.sma)
    #             if self.ask < target and (round(self.momentum, 6) == 0 or self.momentum * self.momentum_prev <= 0):
    #                 self.log_info(f"Close short position  - Buy {-traded_units} units at ask price: {self.ask}, sma: {self.sma}, rsi: {self.rsi}")
    #                 return Trade_Action(self.instrument, -traded_units, self.bid, (self.ask - self.bid), False)