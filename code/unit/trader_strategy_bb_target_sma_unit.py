import argparse
import logging
import os
import random
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path  # if you haven't already done so

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.trader import Trader
from trading.trader_strategy_bb_target_sma import BB_Strategy_SMA_Target_Trader

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

                time.sleep(2)

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

    parser = argparse.ArgumentParser()
    parser.add_argument('pair', type=str, help='pair')
    args = parser.parse_args()

    config_file = os.path.abspath(os.environ.get("oanda_config", "../../config/oanda_demo.cfg"))
    print (f"oanda config file: {config_file}")
    if os.path.exists(config_file) == False:
        logger.error(f"Config file does not exist: {config_file}")
        exit(1) 
 
    
    trader = Trader_Unit_Test(
        conf_file=config_file,
        pairs_file="../trading/pairs.ini",
        instrument=args.pair
    )

    trader.stop_after = 200
    trader.refresh_strategy_time = 30

    # trader.start_trading()
    trader.start_trading()

