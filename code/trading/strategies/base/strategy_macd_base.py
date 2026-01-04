import logging
import sys
from pathlib import Path
import pandas as pd
from trading.strategies.base.strategy_exec import TradingStrategyExec

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.dom.trade import Trade_Action


logger = logging.getLogger()

class TradingStrategyMACD(TradingStrategyExec):
    def __init__(self, trading_strategy, pair_file, api = None, unit_test = False):
        super().__init__(trading_strategy=trading_strategy, pair_file=pair_file, api = api, unit_test = unit_test)

    def calc_indicators(self):
        super().calc_indicators()

        df: pd.DataFrame = self.data

        macd_delta: float = 0.0001
        df["near_macd_crossover"] = 0  # Initialize signal column
        df.loc[(df["sma_long"].shift() - df["ema_short"].shift() >= macd_delta) & (df["sma_long"] - df["ema_short"] < macd_delta), "near_macd_crossover"] = 1  # Bullish crossover
        df.loc[(df["ema_short"].shift() - df["sma_long"].shift() >= macd_delta) & (df["ema_short"] - df["sma_long"] < macd_delta), "near_macd_crossover"] = -1  # Bearish crossover
        df["near_macd_bull"] = (df["near_macd_crossover"] == 1)
        df["near_macd_bear"] = (df["near_macd_crossover"] == -1)
        # df["near_macd_bull"] = df["near_macd_crossover"].rolling(2).apply(lambda x: 1 if 1 in x.values else 0)
        # df["near_macd_bear"] = df["near_macd_crossover"].rolling(2).apply(lambda x: 1 if -1 in x.values else 0)
        
        df["macd_crossover"] = 0  # Initialize signal column
        df.loc[(df["ema_short"].shift() < df["sma_long"].shift()) & (df["ema_short"] > df["sma_long"]), "macd_crossover"] = 1  # Bullish crossover
        df.loc[(df["ema_short"].shift() > df["sma_long"].shift()) & (df["ema_short"] < df["sma_long"]), "macd_crossover"] = -1  # Bearish crossover
        df["macd_bull"] = (df["macd_crossover"] == 1)
        df["macd_bear"] = (df["macd_crossover"] == -1)
        # df["macd_bull"] = df["macd_crossover"].rolling(2).apply(lambda x: 1 if 1 in x.values else 0)
        # df["macd_bear"] = df["macd_crossover"].rolling(2).apply(lambda x: 1 if -1 in x.values else 0)

        self.data = df

    def set_strategy_indicators(self, row: pd.Series):
        super().set_strategy_indicators(row)

        self.near_macd_crossover = row["near_macd_crossover"]
        self.near_macd_bull = bool(row["near_macd_bull"])
        self.near_macd_bear = bool(row["near_macd_bear"])

        self.macd_crossover = row["macd_crossover"]
        self.macd_bull = bool(row["macd_bull"])
        self.macd_bear = bool(row["macd_bear"])



    # def check_if_need_close_trade(self, trading_time) -> Trade_Action: # type: ignore

    #     have_units = self.trading_session.have_units
    #     close_trade, trade_duration_sec = self.need_close_trade(trading_time)
    #     trade_duration_min_sec = divmod(trade_duration_sec, 60)
    #     open_min = trade_duration_min_sec[0]
    #     open_seconds = trade_duration_min_sec[1]
    #     take_profit, trade_pnl = self.take_profit()

    #     if have_units > 0:  # long position
    #         if (close_trade or take_profit or (self.price_max > self.bb_high and self.macd_bear)) and self.price_change < 0:
    #             if not self.backtest:
    #                 logger.info(f"Close long position  - Sell {have_units} units at ask price: {self.bid}, trade duration: {open_min} min {open_seconds} sec, trade profit: {trade_pnl}")
    #             return Trade_Action(trading_time, self.instrument, -have_units, self.bid, False, False, take_profit)
                
    #     elif have_units < 0:  # short position
    #         if (close_trade or take_profit or (self.price_min < self.bb_low and self.macd_bull)) and self.price_change > 0:
    #             if not self.backtest:
    #                logger.info(f"Close short position  - Buy {-have_units} units at ask price: {self.ask}, trade duration: {open_min} min {open_seconds} sec, trade profit: {trade_pnl}")
    #             return Trade_Action(trading_time, self.instrument, -have_units, self.ask, False, False, take_profit)
