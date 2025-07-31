from math import log

from trading.utils.tech_indicators import calculate_rsi, predict_next, calculate_slope, compute_price_momentum
from trading.strategies.base.strategy_base import TradingStrategyBase
from trading.utils import utils
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))


logger = logging.getLogger()

"""
Go Long (buy) when the ask price is below the low Bollinger Band and close trade (sell) when the bid price above the SMA

Go Short (sell) when the bid price is above the high Bollinger Band and close trade (buy) when the ask price below the low Bollinger Band

"""


class TradingStrategyCalc(TradingStrategyBase):
    def __init__(self, trading_strategy, pair_file, api=None, unit_test=False):

        super().__init__(trading_strategy=trading_strategy,pair_file=pair_file, api=api, unit_test=unit_test)

    
    def to_5_min_candles(self, ticker_data_list, trading_time: datetime) -> pd.DataFrame:

        # Filter raw data to the window
        cut_off_time = trading_time - timedelta(minutes=utils.ticker_data_size * utils.frequency_min, seconds=trading_time.second)
        filtered_ticker_data_list = [
            item for item in ticker_data_list if item[0] > cut_off_time
        ]

        # Create initial DataFrame
        ticker_df = pd.DataFrame(filtered_ticker_data_list, columns=["time", "mid", "bid", "ask"])
        ticker_df["time"] = pd.to_datetime(ticker_df["time"], utc=True)
        ticker_df = ticker_df.set_index("time").sort_index()

        # Ensure timezone
        if ticker_df.index.tz is None: # type: ignore
            ticker_df.index = ticker_df.index.tz_localize("UTC") # type: ignore
        else:
            ticker_df.index = ticker_df.index.tz_convert("UTC") # type: ignore

        ticker_df.rename(columns={"mid": "close"}, inplace=True)

        df_open = ticker_df["close"].resample(f"{utils.frequency_min}min", label='right', closed='right').first()
        df_open.name = "open"
        df_mid = ticker_df[["close", "ask", "bid"]].resample(f"{utils.frequency_min}min", label='right', closed='right').last()
        df_high = ticker_df["close"].resample(f"{utils.frequency_min}min", label='right', closed='right').max()
        df_high.name = "high"
        df_low = ticker_df["close"].resample(f"{utils.frequency_min}min", label='right', closed='right').min()
        df_low.name = "low"

        # Merge all into one DataFrame
        df_consolidated = pd.concat([df_open, df_mid, df_low, df_high], axis=1).sort_index()

        # Logging
        # logger.info(
        #     f"price data queue size: {len(ticker_data_list)}, "
        #     f"filtered price data size: {len(filtered_ticker_data_list)}, "
        #     f"ticker data size: {len(df_consolidated.index)}"
        # )

        return df_consolidated


    def calc_indicators(self):

        df: pd.DataFrame = self.data

        # DEV = self.DEV
        std_dev_long = self.DEV
        period_long = self.SMA
        period_short = self.period_short

        df["close"] = df["close"].fillna(0)
        df["price_change"] = df["close"].pct_change()
        df["price_max"] = df["high"].rolling(self.period_short).max()
        df["price_min"] = df["low"].rolling(self.period_short).min()
        df['predicted'] = df['close'].rolling(window=self.period_short).apply(predict_next)
        df['predicted_error'] = df['predicted'] - df['close']
        df["std_dev_long"] = df["close"].rolling(period_long).std(numeric_only=True)
        df["price_volatility"] = ((df["high"] - df["low"]) / (df["high"] + df["low"]) / 2).rolling(self.period_short).mean()    

        df["rsi_short"] = df["close"].rolling(period_short).apply(calculate_rsi)
        df["rsi_short_max"] = df["rsi_short"].rolling(self.period_short).max()
        df["rsi_short_min"] = df["rsi_short"].rolling(self.period_short).min()
        df["rsi_pct_change"] = df["rsi_short"].pct_change()

        df["sma_long"] = df["close"].rolling(period_long).mean(numeric_only=True)
        df["bb_lower"] = df["sma_long"] - df["std_dev_long"] * std_dev_long
        df["bb_upper"] = df["sma_long"] + df["std_dev_long"] * std_dev_long

        df["ema_short"] = df["close"].ewm(span=period_short, adjust=False).mean()
        df["ema_short_slope"] = df["ema_short"].rolling(window=self.period_short).apply(calculate_slope)
        df["ema_short_slope_min"] = df["ema_short_slope"].rolling(window=self.period_short).min()
        df["ema_short_slope_max"] = df["ema_short_slope"].rolling(window=self.period_short).max()

        df["momentum_short"] = df["close"].rolling(period_short).apply(compute_price_momentum)
        df["momentum_short_min"] = df["momentum_short"].rolling(period_short).min()
        df["momentum_short_max"] = df["momentum_short"].rolling(period_short).max()

        df["momentum_long"] = df["close"].rolling(period_long).apply(compute_price_momentum)

        if self.unit_test:
            logger.info("\n" + df.tail(10).to_string(header=True))

        self.data = df

    def set_strategy_indicators(self, row: pd.Series):  # type: ignore

        logger.debug("Setting strategy indicators")

        if row is None:
            row = self.data.iloc[-1]

        self.price = row["close"]
        self.price_change = row["price_change"]
        self.price_max = row["price_max"]
        self.price_min = row["price_min"]
        self.price_open = row["open"]
        self.price_low = row["low"]
        self.price_high = row["high"]
        self.price_volatility = row["price_volatility"] 
        self.ask = row["ask"]
        self.bid = row["bid"]
        self.predicted = row["predicted"]
        self.predicted_error = row["predicted_error"]
        self.std_dev_long = row["std_dev_long"]

        self.rsi_short = round(row["rsi_short"], 4)
        self.rsi_short_max = round(row["rsi_short_max"], 4)
        self.rsi_short_min = round(row["rsi_short_min"], 4)
        self.rsi_pct_change = round(row["rsi_pct_change"], 4)
        
        
        self.sma_long = row["sma_long"]
        self.bb_low = row["bb_lower"]
        self.bb_high = row["bb_upper"]

        self.ema_short = row["ema_short"]
        self.ema_short_slope = row["ema_short_slope"]
        self.ema_short_slope_min = row["ema_short_slope_min"]
        self.ema_short_slope_max = row["ema_short_slope_max"]

        self.momentum_short = row["momentum_short"]
        self.momentum_short_min = row["momentum_short_min"]
        self.momentum_short_max = row["momentum_short_max"]

        self.momentum_long = row["momentum_long"]
