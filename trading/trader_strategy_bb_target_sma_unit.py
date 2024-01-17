import threading
import random
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from trader_strategy_bb_target_sma import BB_Strategy_SMA_Target_Trader

logger = logging.getLogger("trader_oanda")

class Trader_Unit_Test(BB_Strategy_SMA_Target_Trader):
    
    def __init__(self, conf_file, pairs_file, instrument):
        super().__init__(conf_file, pairs_file, instrument, unit_test=True)

    
    def start_trading_random(self):

        logger.info("\n" + 100 * "-")

        try:
            logger.info ("Started New Trading Session")
            logger.info (f"Getting  candles for: {self.instrument}")
            self.strategy.data = self.get_most_recent(self.instrument, self.days)

            logger.info ("Starting Refresh Strategy Thread")
            self.refresh_thread = threading.Thread(target=self.refresh_strategy, args=(self.refresh_strategy_time,))
            self.refresh_thread.start()

            time.sleep(1)

            logger.info (f"Starting to stream for: {self.instrument}")
            for i in range(self.stop_after):

                self.ticks = i
                tick_time, bid, ask = self.get_tick()
                self.on_success(tick_time, bid, ask)

                time.sleep(float(2))

            self.terminate_session("Finished Trading Session")

            
        except Exception as e:
            logger.exception("Exception occurred")
            self.terminate_session("Finished Trading Session with Errors")
        finally:
            logger.info("Stopping Refresh Strategy Thread")
            self.stop_refresh = True
            if self.refresh_thread is not None and self.refresh_thread.is_alive():
                self.refresh_thread.join(timeout=self.refresh_strategy_time)
                logger.info("Stopped Refresh Strategy Thread")
    
        
    def get_tick(self):

        num_1 = random.uniform(self.strategy.bb_lower * (1 - .1), self.strategy.bb_upper * (1 + .1))
        num_2 = random.uniform(self.strategy.bb_lower * (1 - .1), self.strategy.bb_upper * (1 + .1))

        ask = max(num_1, num_2)
        bid = min(num_1, num_2)
        time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")   # "%d/%m/%Y, %H:%M:%S"  2023-12-19T13:28:35.194571445Z

        return time, bid, ask

if __name__ == "__main__":
    # insert the file path of your config file below!

    args = sys.argv[1:]

    pair = args[0]


    trader = Trader_Unit_Test(
        conf_file="oanda.cfg",
        pairs_file="pairs.ini",
        instrument=pair
    )
    trader.stop_after = 5
    trader.refresh_strategy_time = 60

    # trader.start_trading()
    trader.start_trading_random()

