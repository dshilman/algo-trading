import configparser
import logging
import sys

from trader import Order, Strategy, Trade_Action, Trader

logger = logging.getLogger("trader_oanda")

class BB_to_SMA_Strategy(Strategy):
    def __init__(self, instrument, pairs_file):
        super().__init__(instrument, pairs_file)


    def determine_action(self, bid, ask, have_units, units_to_trade) -> Trade_Action:
        
        price = round((bid + ask)/2, 6)
        spread = round(ask - bid, 4)
        target = self.target
        instrument = self.instrument

        if have_units != 0:  # if already have positions
            logger.debug(f"Have {have_units} positions, checking if need to close")
            trade = self.check_if_need_close_trade(instrument, have_units, price, target, spread)
            if trade is not None:
                return trade

        # check if need to open a new position
        logger.debug(f"Have {have_units} positions, checking if need to open")
        trade = self.check_if_need_open_trade(instrument, have_units, price, target, spread, units_to_trade)
        if trade is not None:
            return trade

        return None

    def check_if_need_open_trade(self, instrument, have_units, price, target, spread, units_to_trade):
        
        if spread >= (self.bb_upper - target):                            
            logger.warning (f"Current spread: {spread} is too large for price: {price} and target: {target}")
            return None
        
        
        # if abs(have_units) <= units_to_trade:
        if have_units == 0:
            
            signal = 0

            # if price < self.bb_lower and self.rsi < 30 and price > self.price_min:
            # if price < self.bb_lower and self.rsi < 30 and self.rsi > self.rsi_min: # if price is below lower BB, BUY
            if price < self.bb_lower and self.rsi < 30 and self.rsi > self.rsi_min and price > self.price_min: # if price is below lower BB, BUY
                signal = 1
                logger.info(f"Go Long - BUY at price: {price}, rsi: {self.rsi}")
            # elif price > self.bb_upper and self.rsi > 70 and price < self.price_max:
            # elif price > self.bb_upper and self.rsi > 70 and self.rsi < self.rsi_max:  # if price is above upper BB, SELL
            elif price > self.bb_upper and self.rsi > 70 and self.rsi < self.rsi_max and price < self.price_max:  # if price is above upper BB, SELL
                signal = -1
                logger.info(f"Go Short - SELL at price: {price}, rsi: {self.rsi}")
            
            """
                Trade 1: +1,000 EUR/USD +SL @ 1.05
                Trade 2: +1,000 EUR/USD +SL @ 1.05
                Trade 2 is cancelled because all trades with a SL, TP, or TS must have a unique size
            """
            if signal != 0:
                return Trade_Action(instrument, signal * (units_to_trade + (0 if have_units == 0 else 1)), price, target, spread, True)
                

        return None


    def check_if_need_close_trade(self, instrument, have_units, price, target, spread):

        signal = 0

        if have_units > 0:  # if already have long positions
            # if price > target and price < self.price_max:  # if price is above target SMA, SELL           
            # if price > target and self.rsi < self.rsi_max:  # if price is above target SMA, SELL
            if price > target and self.rsi < self.rsi_max and price < self.price_max:  # if price is above target SMA, SELL
                signal = -1
                logger.info(f"Close long position - Sell {have_units} units at price: {price}, sma: {target}, rsi: {self.rsi}")
        elif have_units < 0:  # if alredy have short positions
            # if price < target and price > self.price_min:  # price is below target SMA, BUY
            # if price < target and self.rsi > self.rsi_min:
            if price < target and self.rsi > self.rsi_min and price > self.price_min:  # price is below target SMA, BUY
                signal = 1
                logger.info(f"Close short position  - Buy {have_units} units at price: {price}, sma: {target}, rsi: {self.rsi}")

        """
            Negative sign if front of have_units "-have_units" means close the existing position
        """
        if signal != 0:
            return Trade_Action(instrument, -have_units, price, target, spread, False)

        return None




    def create_order(self, trade_action: Trade_Action, sl_perc, tp_perc, have_units) -> Order:
        
        order = None

        if trade_action.open_trade:
            if sl_perc:
                if trade_action.spread / trade_action.price >= sl_perc:
                    logger.warning(f"Current spread: {trade_action.spread} is too large for price: {trade_action.price} and sl_perc: {sl_perc}")
                    return None
                """
                    Have been getting STOP_LOSS_ON_FILL_DISTANCE_PRECISION_EXCEEDED when trading GBP_JPY
                    I assume that the price is too high for 4 digit decimals, thus adding a rule
                    if the price is grater that $100, do not use decimals for stop loss
                """
                sl_dist = round(trade_action.price * sl_perc, (4 if trade_action.price < 100 else 0))

            else:
                sl_dist = None

            if tp_perc:
                tp_price = round(trade_action.price + (1 if trade_action.units > 0 else -1) * trade_action.price * tp_perc, 4)
            else:
                tp_price = None

        comment = None
        if have_units >= 0 and trade_action.units > 0:
            comment = "Going Long"
        elif have_units <= 0 and trade_action.units < 0:
            comment = "Going Short"
        elif have_units > 0 and trade_action.units < 0:
            comment = "Closing Long"
        elif have_units < 0 and trade_action.units > 0:
            comment = "Closing Short"

        order = Order(
            instrument = trade_action.instrument,
            price = trade_action.price,
            trade_units = trade_action.units,
            sl_dist = sl_dist,
            tp_price = str(tp_price),
            comment = comment
        )
        logger.debug(order)

        return order


class BB_Strategy_SMA_Target_Trader(Trader):
    def __init__(self, conf_file, pairs_file, instrument, unit_test = False):

        strategy = BB_to_SMA_Strategy(instrument, pairs_file)

        super().__init__(conf_file, pairs_file, strategy, unit_test)


if __name__ == "__main__":

    args = sys.argv[1:]

    pair = args[0]

    
    trader = BB_Strategy_SMA_Target_Trader(
        conf_file="oanda.cfg",
        pairs_file="pairs.ini",
        instrument=pair
    )
    trader.start_trading()
