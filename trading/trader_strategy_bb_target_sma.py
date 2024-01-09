import configparser
import logging
import sys

from trader import Order, Strategy, Trade_Action, Trader

logger = logging.getLogger("trader_oanda")
logger.setLevel(logging.INFO)


class BB_to_SMA_Strategy(Strategy):
    def __init__(self, instrument, pairs_file):
        super().__init__(instrument, pairs_file)


    def determine_action(self, bid, ask, units) -> Trade_Action:
        trade_action = None
        signal = 0
        price = round((bid + ask) / 2, 4)
        spread = round(ask - bid, 4)
        target = round(self.target, 4)
        instrument = self.instrument

        if units > 0:  # if already have long positions
            logger.debug(f"Have {units} positions, checking if need to close")
            # target = self.target + spread
            # if bid > target:  # if price is above target SMA, SELL
            if price > target and self.slope < 0:  # if price is above target SMA, SELL
                signal = -1
                # price = bid
                logger.info(
                    f"Close {units} long position - signal SELL at price: {price}, sma: {self.target}, spread: {spread}, slope: {self.slope}"
                )
        elif units < 0:  # if alredy have short positions
            # target = self.target - spread
            # if ask < target:  # price is below target SMA, BUY
            if price < target and self.slope > 0:  # price is below target SMA, BUY
                signal = 1
                # price = ask
                logger.info(
                    f"Close {units} short position - Signal BUY at price: {price}, sma: {self.target}, spread: {spread}, slope: {self.slope}"
                )
        else:  # if no positions
            logger.debug("Don't have any positions, checking if need to open")
            if spread >= (self.bb_upper - target):
                signal = 0                
                logger.warning (f"Current spread: {spread} is too large for price: {price} and target: {target}")
            else:
                # if ask < self.bb_lower:  # if price is below lower BB, BUY
                # if price < self.bb_lower and self.rsi <= 30 and self.slope5 > 0: # if price is below lower BB, BUY
                if price < self.bb_lower and self.slope > 0: # if price is below lower BB, BUY

                    signal = 1
                    # price = ask
                    logger.info(
                        f"Signal BUY at price: {price}, bb_lower: {self.bb_lower}, spread: {spread}, rsi: {self.rsi}, slope: {self.slope}"
                    )
                # elif bid > self.bb_upper:  # if price is above upper BB, SELL
                # elif price > self.bb_upper and self.rsi >= 70:  # if price is above upper BB, SELL
                elif price > self.bb_upper and self.slope < 0:  # if price is above upper BB, SELL

                    signal = -1
                    # price = bid
                    logger.info(
                        f"Signal SELL at price: {price}, bb_upper: {self.bb_upper}, spread: {spread}, rsi: {self.rsi}, slope: {self.slope}"
                    )
          
        trade_action = Trade_Action(signal, instrument, price, target, spread)
        logger.debug(trade_action)

        return trade_action

    def create_order(self, trade_action: Trade_Action, sl_perc, tp_perc, have_units, units_to_trade) -> Order:
        
        order = None

        if trade_action.signal == 0:
            return None

        if sl_perc:
            if trade_action.spread / trade_action.price >= sl_perc:
                logger.warning(f"Current spread: {trade_action.spread} is too large for price: {trade_action.price} and sl_perc: {sl_perc}")
                return None
            # sl_dist = round(trade_action.price - trade_action.signal * trade_action.price * sl_perc, 4)
            sl_dist = round(trade_action.price * sl_perc, 2)

        else:
            sl_dist = None

        if tp_perc:
            tp_price = round(trade_action.price + trade_action.signal * trade_action.price * tp_perc, 2)
        else:
            tp_price = None

        if trade_action.signal == 1:  # if signal is BUY
            logger.info("Signal = BUY")
            if have_units <= 0:  # has short positions
                trade_units = max(units_to_trade, have_units)

                order = Order(
                    signal = trade_action.signal,
                    instrument = trade_action.instrument,
                    price = trade_action.price,
                    trade_units = trade_units,
                    sl_dist = sl_dist,
                    tp_price = tp_price,
                    comment = "Going Long" if have_units == 0 else "Closing Short"
                )
            else:  # Already have a LONG position
                logger.info(
                    f"Already have {have_units} long positions...skipping trade"
                )
        elif trade_action.signal == -1:  # if signal is SELL
            logger.info("Signal = SELL")
            if have_units >= 0:
                trade_units = min(-units_to_trade, have_units)
                
                order = Order(
                    signal = trade_action.signal,
                    instrument = trade_action.instrument,
                    price = trade_action.price,
                    trade_units = trade_units,
                    sl_dist = sl_dist,
                    tp_price = tp_price,
                    comment = "Going Short" if have_units == 0 else "Closing Long"
                )
            else:  # Already have a SHORT position
                logger.info(
                    f"Already have {have_units} short positions...skipping trade"
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

