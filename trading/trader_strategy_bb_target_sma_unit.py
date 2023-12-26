import threading
import random
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from trader_strategy_bb_target_sma import BB_Strategy_SMA_Target_Trader

logger = logging.getLogger("trader_oanda")
logger.setLevel(logging.INFO)


class Trader_Unit_Test(BB_Strategy_SMA_Target_Trader):
    def __init__(self, conf_file, instrument, units_to_trade, SMA, dev, sl_perc=None, tp_perc=None, print_trades = False):
        super().__init__(conf_file, instrument, units_to_trade, SMA, dev, sl_perc, tp_perc, print_trades)
        self.unit_test = True

    
    def start_trading(self, days = 1, stop_after = 10):

        logger.info("\n" + 100 * "-")

        refresh_thread = None
        try:
            logger.info ("Started New Trading Session")
            logger.info (f"Getting  candles for: {self.instrument}")
            self.strategy.data = self.get_most_recent(self.instrument, days)

            logger.info ("Define strategy for the first time")
            self.strategy.define_strategy()

            logger.info ("Starting Refresh Strategy Thread")
            refresh_thread = threading.Thread(target=self.refresh_strategy, args=(self.refresh_strategy_time,))
            refresh_thread.start()

            logger.info ("Check  Positions")
            self.check_positions()

            logger.info (f"Starting to stream for: {self.instrument}")

            for i in range(stop_after):

                self.ticks = i
                tick_time, bid, ask = self.get_tick()
                self.on_success(tick_time, bid, ask)

                time.sleep(float(1))

            self.terminate_session("Finished Trading Session")

            
        except Exception as e:
            logger.exception("Exception occurred")
            self.terminate_session("Finished Trading Session with Errors")
        finally:
            self.stop_refresh = True

            if refresh_thread is not None and refresh_thread.is_alive():
                refresh_thread.join()    
        
        
    def get_tick(self):

        num_1 = random.uniform(self.strategy.bb_lower * (1 - .1), self.strategy.bb_upper * (1 + .1))
        num_2 = random.uniform(self.strategy.bb_lower * (1 - .1), self.strategy.bb_upper * (1 + .1))

        ask = max(num_1, num_2)
        bid = min(num_1, num_2)
        time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")   # "%d/%m/%Y, %H:%M:%S"  2023-12-19T13:28:35.194571445Z

        return time, bid, ask

if __name__ == "__main__":
    # insert the file path of your config file below!
    days = 1
    stop_after = 10
    print_trades = False
    args = sys.argv[1:]

    print (f"argument length: {len(args)}")

    if args and len(args) > 0:
        days = int(args[0])

        if args and len(args) > 1:
            stop_after = int(args[1])

            if args and len(args) > 2:
                print_trades = bool(args[2])


    trader = Trader_Unit_Test(
        conf_file="oanda.cfg",
        instrument="EUR_USD",
        units_to_trade=10000,
        SMA=100,
        dev=2,
        sl_perc=0.001,
        tp_perc=0.002,
        print_trades = print_trades
    )
    trader.start_trading(days=days, stop_after=stop_after)

