import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd


file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.utils.tech_indicators import (
    count_sma_crossover, calculate_rsi, calculate_slope, calculate_ema)
from trading.strategies.base.strategy_exec import TradingStrategyExec
from trading.dom.trade import Trade_Action

logger = logging.getLogger()

"""
Go Long (buy) when the ask price is below the low Bollinger Band and close trade (sell) when the bid price above the SMA

Go Short (sell) when the bid price is above the high Bollinger Band and close trade (buy) when the ask price below the low Bollinger Band

"""
class TradingStrategy(TradingStrategyExec):
    def __init__(self, trading_strategy, pair_file, api = None, unit_test = False):
        super().__init__(trading_strategy=trading_strategy, pair_file=pair_file, api = api, unit_test = unit_test)



    def calc_indicators(self):
        super().calc_indicators()

        df: pd.DataFrame = self.data
 
        # df["rsi_short"] = ((df["eopen"] + df["low"])/2).rolling(self.period_short).apply(lambda x: calculate_rsi(x, self.period_short))

        # df["rsi_short_max"] = df["rsi_short"].rolling(5).max()
        # df["rsi_short_min"] = df["rsi_short"].rolling(5).min()

        # df["price_max"] = df["high"].rolling(5).max()
        # df["price_min"] = df["low"].rolling(5).min()


        df["ema_bb_high_divergance"] = df["bb_upper"] - df["ema_short"]
        df["ema_bb_high_divergance_mean"] = df["ema_bb_high_divergance"].rolling(self.period_short).mean()

        df["ema_bb_low_divergance"] = df["ema_short"] - df["bb_lower"]
        df["ema_bb_low_divergance_mean"] = df["ema_bb_low_divergance"].rolling(self.period_short).mean()
        
        self.data = df

    def set_strategy_indicators(self, row: pd.Series):
        super().set_strategy_indicators(row)

        self.ema_bb_high_divergance = row["ema_bb_high_divergance"]
        self.ema_bb_low_divergance = row["ema_bb_low_divergance"]

        self.ema_bb_high_divergance_mean = row["ema_bb_high_divergance_mean"]
        self.ema_bb_low_divergance_mean = row["ema_bb_low_divergance_mean"]

    def check_if_need_open_trade(self, trading_time) -> Trade_Action: # type: ignore
   
        if  round(self.std_dev_long, 4) >= self.trading_std and self.price_volatility > self.trading_price_volatility:

            if self.rsi_short_max > self.high_rsi \
                and self.price_max > self.bb_high and self.price_ema_crossover_down:
                    if not self.backtest:
                        logger.info(f"Go Short - Sell {self.units_to_trade} units at ask price: {self.bid}")
                    return Trade_Action(trading_time, self.instrument, -self.units_to_trade, self.bid, True, False, False)
                        

            elif self.rsi_short_min < self.low_rsi \
                and self.price_min < self.bb_low and self.price_ema_crossover_up:
                    if not self.backtest:
                        logger.info(f"Go Long - Buy {self.units_to_trade} units at ask price: {self.ask}")
                    return Trade_Action(trading_time, self.instrument, self.units_to_trade, self.ask, True, False, False)                    


    def check_if_need_close_trade(self, trading_time) -> Trade_Action: # type: ignore

        have_units = self.trading_session.have_units
        close_trade = self.need_close_trade(trading_time)
        take_profit, tp_price = self.take_profit()

        if have_units > 0:  # long position
            if close_trade or take_profit or self.macd_crossover_bear or self.price > self.bb_high:
                if not self.backtest:
                    logger.info(f"Close long position  - Sell {have_units} units at ask price: {self.bid}")
                return Trade_Action(trading_time, self.instrument, -have_units, tp_price if take_profit else self.bid, False, False, take_profit)
                
        elif have_units < 0:  # short position
            if close_trade or take_profit or self.macd_crossover_bull or self.price < self.bb_low:

                if not self.backtest:
                   logger.info(f"Close short position  - Buy {-have_units} units at ask price: {self.ask}")
                return Trade_Action(trading_time, self.instrument, -have_units, tp_price if take_profit else self.ask, False, False, take_profit)



    def print_indicators(self):
        super().print_indicators()
        logger.info(f"low_bb_diverge: {self.ema_bb_low_divergance > self.ema_bb_low_divergance_mean}, high_bb_diverge: {self.ema_bb_high_divergance > self.ema_bb_high_divergance_mean}")
