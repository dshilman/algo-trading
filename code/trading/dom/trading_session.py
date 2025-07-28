import logging
from datetime import datetime, timedelta, timezone
from tabulate import tabulate
from pathlib import Path
import sys
file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from dom.trade import Trade_Action
from utils import utils

logger = logging.getLogger()
class Trading_Session():

    def __init__(self, instrument):
        
        self.instrument = instrument
        self.trades = []
        self.pl: float = 0
        self.outstanding: float = 0
        self.go_short: int = 0
        self.long_trades: int = 0
        self.short_trades: int = 0
        self.long_trades_close: int = 0
        self.short_trades_close: int = 0
        self.trade_cost: float = 0
        self.have_units: int = 0
        self.columns = ["datetime", "trade", "units", "price", "trade_pnl", "trade_duration", "total pnl"]

        super().__init__()


    def add_trade(self, trade_action: Trade_Action, date_time, **kwargs):

        trade = None
        trade_pl: float = 0
        trade_duration = None

        if trade_action.open_trade and trade_action.units > 0:
            self.trade_cost = abs(trade_action.units) * trade_action.price
            self.outstanding = (self.outstanding) + (self.trade_cost)      
            self.long_trades = self.long_trades + 1
            trade = "Open Long"
        elif trade_action.open_trade and trade_action.units < 0:
            self.trade_cost = abs(trade_action.units) * trade_action.price
            self.outstanding = (self.outstanding) + (self.trade_cost)   
            self.short_trades = self.short_trades + 1
            trade = "Open Short"
        elif not trade_action.open_trade and trade_action.units < 0:
            self.trade_cost = abs(trade_action.units) * trade_action.price
            trade_pl = self.trade_cost - self.outstanding
            self.pl = self.pl + trade_pl
            duration_divmod = self.calc_duration(date_time)
            trade_duration = f"{int(duration_divmod[0])} hr {int(duration_divmod[1])//60} min"
            self.long_trades_close = self.long_trades_close + 1
            self.outstanding = self.have_units + trade_action.units
            if trade_action.sl_trade:
                trade = "Close Long (SL)"
            elif trade_action.tp_trade:
                trade = "Close Long (TP)"
            else:
                trade = "Close Long"
        elif not trade_action.open_trade and trade_action.units > 0:
            self.trade_cost = abs(trade_action.units) * trade_action.price
            trade_pl = self.outstanding - self.trade_cost
            self.pl = self.pl + trade_pl
            duration_divmod = self.calc_duration(date_time)
            trade_duration = f"{int(duration_divmod[0])} hr {int(duration_divmod[1]//60)} min"
            self.short_trades_close = self.short_trades_close + 1
            self.outstanding = self.have_units + trade_action.units
            if trade_action.sl_trade:
                trade = "Close Short (SL)"
            elif trade_action.tp_trade:
                trade = "Close Short (TP)"
            else:
                trade = "Close Short"
        
        self.have_units = self.have_units + trade_action.units

        self.trades.append([date_time, trade, trade_action.units, trade_action.price, ('' if trade_pl == 0 else '${:,.2f}'.format(trade_pl)), (trade_duration if trade_duration is not None else ""), '${:,.2f}'.format(self.pl)])
       
        return

    def calc_duration(self, date_time):
        trade_duration = divmod((date_time - self.trades[-1][0]).total_seconds(), 3600) if len(self.trades) > 0 else (0, 0)
        return trade_duration


    def has_trades(self) -> bool:
        return len(self.trades) > 0

    def convert_datetime_to_str(self):

        for trade in self.trades:
            trade[0] = trade[0].strftime("%Y-%m-%d %H:%M:%S")

        return
    def print_trades(self):

        self.convert_datetime_to_str()
        logger.info(f"Finished Trading {self.instrument} with PL: {'${:,.2f}'.format(self.pl)}, # of long trades: {self.long_trades}, # of short trades: {self.short_trades}, open trades: {self.long_trades - self.long_trades_close + self.short_trades - self.short_trades_close}")
        logger.info("\n" + 100 * "-") 
        logger.info("\n" + tabulate(self.trades, headers = self.columns))
        logger.info("\n" + 100 * "-")
        logger.info(f"Finished Trading {self.instrument} with PL: {'${:,.2f}'.format(self.pl)}, # of long trades: {self.long_trades}, # of short trades: {self.short_trades}, open trades: {self.long_trades - self.long_trades_close + self.short_trades - self.short_trades_close}")
        self.trades.clear()

    def to_excel(self, file_name):

        self.convert_datetime_to_str()

        import pandas as pd
        df = pd.DataFrame(self.trades, columns = self.columns)
        df.to_excel(file_name, index=False)

        return

    def to_pickle(self, file_name):
        import pandas as pd
        df=pd.DataFrame(self.trades, columns = self.columns)
        df.to_pickle(file_name)