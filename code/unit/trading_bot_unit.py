import argparse
import logging
import os
import sys
from pathlib import Path

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.trading_bot import Trader


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('pair', type=str, help='pair')
    args = parser.parse_args()

    config_file = os.path.abspath(os.environ.get("oanda_config", "../../config/oanda_demo.cfg"))
    print (f"oanda config file: {config_file}")
    if os.path.exists(config_file) == False:
        print(f"Config file does not exist: {config_file}")
        exit(1) 
 
    
    trader = Trader(
        conf_file=config_file,
        pair_file="../trading/pairs.ini",
        instrument=args.pair,
        unit_test=True
    )

      # trader.start_trading()
    trader.start_trading(stop_after=500)

    # python trading_bot_unit.py EUR_USD
