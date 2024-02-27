import configparser
import json
import logging
import sys
from datetime import datetime, time
from pathlib import Path

import pandas as pd
from tabulate import tabulate

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.api import OANDA_API
from trading.dom.order import Order
from trading.dom.trade import Trade_Action
from trading.dom.trading_session import Trading_Session
from trading.errors import PauseTradingException
from trading.tech_indicatrors import calculate_slope, calculate_rsi, calculate_momentum

logger = logging.getLogger()

class TradingStrategy():
    def __init__(self, instrument, pair_file, api: OANDA_API = None, unit_test = False):
        super().__init__()

        self.trading_session = Trading_Session()

        self.instrument = instrument
        self.api = api
        self.unit_test = unit_test
        config = configparser.ConfigParser()  
        config.read(pair_file)
        self.sma_value = int(config.get(instrument, 'SMA'))
        self.dev = float(config.get(instrument, 'dev'))
        self.units_to_trade = int(config.get(instrument, 'units_to_trade'))
        self.sl_perc = float(config.get(self.instrument, 'sl_perc'))
        self.tp_perc = float(config.get(self.instrument, 'tp_perc'))
        self.low_rsi = float(config.get(self.instrument, 'low_rsi'))
        self.high_rsi = float(config.get(self.instrument, 'high_rsi'))
        self.pause_start = int(config.get(self.instrument, 'pause_start'))
        self.pause_end = int(config.get(self.instrument, 'pause_end'))


        self.data = None
        # Caculated attributes
        self.bb_upper =  None
        self.bb_lower =  None
        self.sma = None

        self.price = None
        self.price_max = None
        self.price_min = None
        self.price_momentum = None
        self.price_momentum_prev = None

        
        self.rsi = None
        self.rsi_min = None
        self.rsi_max = None
        self.rsi_momentum = None
        self.rsi_momentum_prev = None


    def execute_strategy(self, have_units):

        trade_action = self.determine_trade_action(have_units)        

        if trade_action is not None:
            # logger.info(f"trade_action: {trade_action}")
            
            order = self.create_order(trade_action, self.sl_perc, self.tp_perc, have_units)

            if order is not None:
                have_units = self.submit_order(order, have_units)

        if trade_action is not None and trade_action.sl_trade:
            raise PauseTradingException(2)

        return have_units

    def calc_indicators(self, resampled_tick_data: pd.DataFrame = None):
        
        df = self.data.copy()
        
        if resampled_tick_data is not None and resampled_tick_data.size > 0:
            df = pd.concat([df, resampled_tick_data])
      
        df = df.tail(self.sma_value * 3)
        df = df.reset_index().drop_duplicates(subset='time', keep='last').set_index('time')

                
        # ******************** define your strategy here ************************
        df["SMA"] = df[self.instrument].rolling(self.sma_value).mean()

        std = df[self.instrument].rolling(self.sma_value).std() * self.dev
        df["Lower"] = df["SMA"] - std
        df["Upper"] = df["SMA"] + std

        rsi_periods = int(self.sma_value/2)
        df["RSI"] = df[self.instrument][-self.sma_value:].rolling(rsi_periods).apply(lambda x: calculate_rsi(x.values, rsi_periods))

        df ["momentum"] = df[self.instrument][-self.sma_value:].rolling(8).apply(lambda x: calculate_momentum(x.iloc[0], x.iloc[-1]))

        df ["rsi_momentum"] = df.RSI[-self.sma_value:].rolling(8).apply(lambda x: calculate_momentum(x.iloc[0], x.iloc[-1]))
  
        self.ask = round(df.ask.iloc[-1], 6)
        self.bid = round(df.bid.iloc[-1], 6)
        self.sma = round(df.SMA.iloc[-1], 6)
        
        self.bb_lower = round(df.Lower.iloc[-1], 6)
        self.bb_upper =  round(df.Upper.iloc[-1], 6)
        # self.rsi = round(df.RSI.iloc[-1], 4)
        last_rsi = df.RSI[-8:].values
        self.rsi = last_rsi[-1]
        self.rsi_min = last_rsi.min()
        self.rsi_max = last_rsi.max()
        self.rsi_momentum = round(df ["rsi_momentum"].iloc[-1], 6)
        self.rsi_momentum_prev = round(df ["rsi_momentum"].iloc[-2], 6)

        last_momentum = df.momentum[-8:].values
        self.price_momentum = round(last_momentum[-1], 6)
        self.price_momentum_prev = round(last_momentum[-2], 6)
        last_prices = df[self.instrument][-8:].values
        self.price = round(last_prices[-1], 6)
        self.price_min = round(last_prices[-8:].min(), 6)
        self.price_max = round(last_prices.max(), 6)

        logger.debug("\n" + df[-10:].to_string(header=True))
  
        self.print_indicators()
        
        self.data = df.copy()

    
    def submit_order(self, order: Order, units: int):

        logger.info(f"Submitting Order: {order}")
        if not self.unit_test:        
            result = self.api.create_order(order=order)
            self.report_trade(result)
            if "rejectReason" not in result:
                units = units + order.units
                logger.info(f"New # of {order.instrument} units: {units}")
            else:
                error = f"Order was not filled: {result ['type']}, reason: {result['rejectReason']}"
                logger.error(error)
                raise Exception(error)
        else:
            units = units + order.units
            logger.info(f"New # of {order.instrument} units: {units}")

        return units

    def report_trade(self, order):

        logger.info("\n" + 100 * "-" + "\n")
        logger.info("")
        logger.info("\n" + self.data[-10:].to_string(header=True))
        logger.info("")
        self.print_indicators()
        logger.info("")
        logger.info(json.dumps(order, indent = 2))
        logger.info("\n" + 100 * "-" + "\n")

    def determine_trade_action(self, have_units, date_time = None) -> Trade_Action:

        if date_time is None:
            date_time = datetime.utcnow()

        if have_units != 0:  # if already have positions
            logger.debug(f"Have {have_units} positions, checking for stop loss")
            trade_action = self.check_for_sl(have_units)
            if trade_action is not None:
                return trade_action

            logger.debug(f"Have {have_units} positions, checking if need to close")
            if len (self.trading_session.trades) > 0:
                trade = self.check_if_need_close_trade_from_hist(have_units)
            else:
                trade = self.check_if_need_close_trade(have_units)
    
            if trade is not None:
                return trade

        else:        
            logger.debug(f"Have {have_units} positions, checking if need to open")
            trade = self.check_if_need_open_trade(have_units, date_time)
            if trade is not None:
                return trade

        return None


    def check_if_need_open_trade(self, have_units, date_time = None):
        
        if self.pause_trading(date_time):
            return

        spread = round(self.ask - self.bid, 4)
        # check if need to open a new position
        if 2.5 * spread >= abs(self.bb_upper - self.sma):                            
            logger.debug(f"Current spread: {spread} is too large to trade for possible gain: {round(abs(self.bb_upper - self.sma), 6)}")
            return None

        if self.ask < self.bb_lower and self.has_low_rsi() and self.reverse_rsi_momentum(): # if price is below lower BB, BUY
        # if self.ask <= self.bb_lower and self.has_low_rsi() and self.price_momentum * self.price_momentum_prev <= 0: # if price is below lower BB, BUY
            signal = 1
            # logger.info(f"Go Long - BUY at ask price: {self.ask}, rsi: {self.rsi}")
            return Trade_Action(self.instrument, signal * (self.units_to_trade + (0 if have_units == 0 else 1)), self.ask, spread, "Go Long - Buy", True, False)

        elif self.bid > self.bb_upper and self.has_high_rsi() and self.reverse_rsi_momentum():  # if price is above upper BB, SELL
        # elif self.bid >= self.bb_upper and self.has_high_rsi() and self.price_momentum * self.price_momentum_prev <= 0:
            signal = -1
            # logger.info(f"Go Short - SELL at bid price: {self.bid}, rsi: {self.rsi}")
            return Trade_Action(self.instrument, signal * (self.units_to_trade + (0 if have_units == 0 else 1)), self.bid, spread, "Go Short - Sell", True, False)
            
        return
    

    def reverse_rsi_momentum(self):
        
        return self.rsi_momentum * self.rsi_momentum_prev <= 0
        

    def reverse_price_momentum(self):
        # return self.price_momentum * self.price_momentum_prev <= 0
        return self.price < self.price_max if self.price_momentum < 0 else self.price > self.price_min
        
    def has_high_rsi(self):

        return self.rsi_max > self.high_rsi
    
    def has_low_rsi(self):
        
        return self.rsi_min < self.low_rsi
    
    def check_if_need_close_trade_from_hist(self, have_units):

        if len (self.trading_session.trades) > 0:
            transaction_price =  self.trading_session.trades[-1][3]
            # traded_units = self.trading_session.trades[-1][2]

            trade_units = have_units

            if trade_units > 0: # long position
                # target = self.sma
                target = min(self.sma,  transaction_price + 2 * (self.ask - self.bid))
                if self.bid > target and self.reverse_price_momentum():
                    # logger.info(f"Close long position - Sell {-traded_units} units at bid price: {self.bid}, target: {target}")
                    return Trade_Action(self.instrument, -trade_units, self.ask, (self.ask - self.bid), "Close Long - Sell", False, False)

            if trade_units < 0: # short position
                target = max(self.sma,  transaction_price - 2 * (self.ask - self.bid))
                # target = self.sma
                if self.ask < target and self.reverse_price_momentum():
                    # logger.info(f"Close short position  - Buy {-traded_units} units at ask price: {self.ask}, target: {target}")
                    return Trade_Action(self.instrument, -trade_units, self.bid, (self.ask - self.bid), "Close Short - Buy", False, False)
        
        return None

    
    def check_if_need_close_trade(self, have_units):

        if have_units > 0: # long position
                target = self.sma
                if self.bid > target and self.reverse_price_momentum():
                    logger.info(f"Close long position - Sell {-have_units} units at bid price: {self.bid}, target: {target}")
                    return Trade_Action(self.instrument, -have_units, self.ask, (self.ask - self.bid), "Close Long - Sell", False, False)

        if have_units < 0: # short position
            target = self.sma
            if self.ask < target and self.reverse_price_momentum():
                logger.info(f"Close short position  - Buy {-have_units} units at ask price: {self.ask}, target: {target}")
                return Trade_Action(self.instrument, -have_units, self.bid, (self.ask - self.bid), "Close Short - Buy", False, False)

        return None

    def check_for_sl(self, have_units):

        if len (self.trading_session.trades) == 0:
            return None

        transaction_price =  self.trading_session.trades[-1][3]
        traded_units = self.trading_session.trades[-1][2]

        if have_units < 0:
            current_loss_perc = round((self.ask - transaction_price)/transaction_price, 4)
            if current_loss_perc >= self.sl_perc  - .0005:
                logger.info(f"Close short position, - Stop Loss Buy, short price {transaction_price}, current ask price: {self.ask}, loss: {current_loss_perc}")
                return Trade_Action(self.instrument, -traded_units, self.ask, (self.ask - self.bid), "Close Short - Stop Loss Buy", False, True)

        if have_units > 0:
            current_loss_perc = round((transaction_price - self.bid)/transaction_price, 4)
            if current_loss_perc >= self.sl_perc - .0005:
                logger.info(f"Close long position, - Stop Loss Sell, long price {transaction_price}, current bid price: {self.bid}, lost: {current_loss_perc}")
                return Trade_Action(self.instrument, -traded_units, self.bid, (self.ask - self.bid), "Close Long - Stop Loss Sell", False, True)
        
        return None

    def print_indicators(self):

        indicators = [[self.ask, self.bid, self.sma, self.bb_lower, self.bb_upper, self.rsi, self.rsi_min, self.rsi_max, '{0:f}'.format(self.rsi_momentum), '{0:f}'.format(self.price_momentum)]]
        columns=["ASK PRICE", "BID PRICE", "SMA", "BB_LOW", "BB_HIGH", "RSI", "RSI MIN", "RSI MAX", "RSI MOMENTUM", "PRICE MOMENTUM"]
        logger.info("\n" + tabulate(indicators, headers = columns) + "\n")


    def create_order(self, trade_action: Trade_Action, sl_perc, tp_perc, have_units) -> Order:
        
        sl_dist = None
        tp_price = None

        # if trade_action.open_trade:
        if sl_perc:
            if trade_action.spread / trade_action.price >= sl_perc:
                logger.warning(f"Current spread: {trade_action.spread} is too large for price: {trade_action.price} and sl_perc: {sl_perc}")
                return None
            """
                Have been getting STOP_LOSS_ON_FILL_DISTANCE_PRECISION_EXCEEDED when trading GBP_JPY
                I assume that the price is too high for 4 digit decimals, thus adding a rule
                if the price is grater that $100, do not use decimals for stop loss
            """
            sl_dist = round(trade_action.price * (sl_perc), (4 if trade_action.price < 100 else 0))

            
        if tp_perc:
            tp_price = str(round(trade_action.price + (1 if trade_action.units > 0 else -1) * trade_action.price * tp_perc, (4 if trade_action.price < 100 else 0)))

        self.trading_session.add_trade(trade_action, have_units, self.rsi)

        order = Order(
            instrument = trade_action.instrument,
            price = trade_action.price,
            trade_units = trade_action.units,
            sl_dist = sl_dist,
            tp_price = tp_price
        )
        logger.debug(order)

        return order

    def pause_trading(self, date_time) -> bool:

        logger.debug(f"Date time: {date_time}")

        if self.pause_start != self.pause_end and self.pause_start <= date_time.hour <= self.pause_end:
            return True

        return False