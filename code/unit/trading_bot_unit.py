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


    config_file = os.path.abspath(path="../../config/oanda.cfg")
    print (f"oanda config file: {config_file}")
    if os.path.exists(config_file) == False:
        print(f"Config file does not exist: {config_file}")
        exit(1) 

    parser = argparse.ArgumentParser()
    parser.add_argument('pair', type=str, default = "EUR_USD", help='pair')
    parser.add_argument('--stop', type = int, default=5, help='Stop after')
    args = parser.parse_args()

    
    trader = Trader(
        conf_file=config_file,
        pair_file="../trading/pairs.ini",
        instrument=args.pair,
        unit_test=True
    )

      # trader.start_trading()
    trader.start_trading(stop_after=args.stop)

    # python trading_bot_unit.py EUR_USD --stop 5
