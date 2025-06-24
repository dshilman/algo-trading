import logging
import sys
from pathlib import Path
import pandas as pd

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.strategies.base.strategy_macd_base import TradingStrategyMACD
from trading.dom.trade import Trade_Action

logger = logging.getLogger()

class TradingStrategy(TradingStrategyMACD):
    def __init__(self, trading_strategy, pair_file, api = None, unit_test = False):
        super().__init__(trading_strategy=trading_strategy, pair_file=pair_file, api = api, unit_test = unit_test)

    def calc_indicators(self):
        super().calc_indicators()

        df: pd.DataFrame = self.data
 
        df['price_volatility'] = ((df['high'] - df['low']) / (df['high'] + df['low']) / 2).rolling(5).mean()    

        self.data = df

    def check_if_need_open_trade(self, trading_time) -> Trade_Action: # type: ignore

        if  self.std_dev_long < self.trading_std and self.price_volatility > self.trading_price_volatility:

            if self.macd_crossover_bull and self.rsi_short > self.high_rsi and self.bid < self.bb_high:
                if not self.backtest:
                    logger.info(f"Go Long - Buy {self.units_to_trade} units at ask price: {self.ask}")
                return Trade_Action(trading_time, self.instrument, self.units_to_trade, self.ask, True, False, False)                    


            elif self.macd_crossover_bear and self.rsi_short < self.low_rsi and self.ask > self.bb_low:
                if not self.backtest:
                    logger.info(f"Go Short - Sell {self.units_to_trade} units at ask price: {self.bid}")
                return Trade_Action(trading_time, self.instrument, -self.units_to_trade, self.bid, True, False, False)
        


    def check_if_need_close_trade(self, trading_time) -> Trade_Action: # type: ignore

        have_units = self.trading_session.have_units
        close_trade = self.need_close_trade(trading_time)
        take_profit, tp_price = self.take_profit()

        if have_units > 0:  # long position
            if (close_trade or take_profit) or (self.rsi_short < 30):
                if not self.backtest:
                    logger.info(f"Close long position  - Sell {have_units} units at ask price: {self.bid}")
                return Trade_Action(trading_time, self.instrument, -have_units, tp_price if take_profit else self.bid, False, False, take_profit)
                
        elif have_units < 0:  # short position
            if (close_trade or take_profit) or (self.rsi_short > 70):
                if not self.backtest:
                   logger.info(f"Close short position  - Buy {-have_units} units at ask price: {self.ask}")
                return Trade_Action(trading_time, self.instrument, -have_units, tp_price if take_profit else self.ask, False, False, take_profit)

