import logging
from datetime import datetime, timedelta, timezone
from tabulate import tabulate

from pathlib import Path
import sys
file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from dom.trade import Trade_Action


logger = logging.getLogger()
class Trading_Session():

    def __init__(self, instrument):
        
        self.instrument = instrument
        self.trades = []
        self.pl:float = 0
        self.outstanding: float = 0
        self.go_short: int = 0
        self.long_trades: int = 0
        self.short_trades: int = 0
        self.long_trades_close: int = 0
        self.short_trades_close: int = 0
        self.trade_cost: float = 0
        self.have_units: int = 0
        self.trade_id: int = 0
        self.columns = ["datetime", "trade_id", "trade", "action", "units", "price", "trade_pl", "trade_pl_pct", "pl"]

        super().__init__()


    def __get_trade_new_id(self) -> int:
        
        self.trade_id = self.trade_id + 1
        return self.trade_id

    def add_trade(self, trade_action: Trade_Action, date_time, **kwargs):

        trade = None
        action = None
        trade_pl = None
        trade_pl_pct = None

        if self.have_units >= 0 and trade_action.units > 0:
            self.trade_id = self.__get_trade_new_id()
            self.trade_cost = abs(trade_action.units) * trade_action.price
            self.outstanding = self.outstanding + self.trade_cost      
            trade_pl = 0
            trade_pl_pct = 0        
            self.long_trades = self.long_trades + 1
            trade = "Open Long"
            action = "Buy"
        elif self.have_units <= 0 and trade_action.units < 0:
            self.trade_id = self.__get_trade_new_id()
            self.trade_cost = abs(trade_action.units) * trade_action.price
            self.outstanding = self.outstanding + self.trade_cost      
            trade_pl = 0
            trade_pl_pct = 0        
            self.short_trades = self.short_trades + 1
            trade = "Open Short"
            action = "Sell"
        elif self.have_units > 0 and trade_action.units < 0:
            self.trade_cost = abs(trade_action.units) * trade_action.price
            trade_pl = self.trade_cost - self.outstanding
            self.pl = self.pl + trade_pl
            trade_pl_pct = 0 if self.outstanding == 0 else trade_pl / self.outstanding * 100 
            self.long_trades_close = self.long_trades_close + 1
            self.outstanding = 0
            trade = " Close Long"  + (" (SL)" if trade_action.sl_trade else "")
            action = "Sell"
        elif self.have_units < 0 and trade_action.units > 0:
            self.trade_cost = abs(trade_action.units) * trade_action.price
            trade_pl = self.outstanding - self.trade_cost
            self.pl = self.pl + trade_pl
            trade_pl_pct = 0 if self.outstanding == 0 else trade_pl / self.outstanding * 100
            self.short_trades_close = self.short_trades_close + 1
            self.outstanding = 0
            trade = " Close Short" + (" (SL)" if trade_action.sl_trade else "")
            action = "Buy"
        
        self.have_units = self.have_units + trade_action.units

        self.trades.append([date_time.strftime("%m/%d/%Y %H:%M:%S"), self.trade_id, trade, action, trade_action.units, trade_action.price, '${:,.2f}'.format(trade_pl), '%{:,.4f}'.format(trade_pl_pct), '${:,.2f}'.format(self.pl)])

        return

    def print_trades(self):

        logger.info("\n" + 100 * "-")        
        logger.info("\n" + tabulate(self.trades, headers = self.columns))
        logger.info(f"Finished Trading {self.instrument} with PL: {'${:,.2f}'.format(self.pl)}, # of long trades: {self.long_trades}, # of short trades: {self.short_trades}, open trades: {self.long_trades - self.long_trades_close + self.short_trades - self.short_trades_close}")
        logger.info("\n" + 100 * "-")

    def to_excel(self, file_name):

        import pandas as pd
        df = pd.DataFrame(self.trades, columns = self.columns)
        df.to_excel(file_name, index=False)

        return

    def to_pickle(self, file_name):
        import pandas as pd
        df=pd.DataFrame(self.trades, columns = self.columns)
        df.to_pickle(file_name)