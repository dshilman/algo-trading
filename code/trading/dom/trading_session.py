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

    def __init__(self):
        
        self.trades = []
        self.pl:float = 0
        self.go_short = 0
        self.go_long = 0
        self.close_short = 0
        self.close_long = 0
        self.outstanding = 0
        self.trade_cost = 0
        self.trade_pl = 0
        self.have_units = 0
        self.columns = ["datetime", "transaction", "price", "trade pl", "rsi", "rsi_min", "rsi_max", "total pl"]

        super().__init__()



    def add_trade(self, trade_action: Trade_Action, date_time=None, **kwargs):

        if date_time is None:
            date_time = datetime.utcnow()

        transaction = None
        if self.have_units >= 0 and trade_action.units > 0:
            self.trade_cost = abs(trade_action.units) * trade_action.price
            self.outstanding = self.outstanding + self.trade_cost      
            self.trade_pl = 0      
            self.go_long = self.go_long + 1
            transaction = "Go Long - Buy"
            # logger.info(f"Go Long -- shares: {trade_action.units}, at price: {trade_action.price}, P&L {'${:,.2f}'.format(self.pl)}")
        elif self.have_units <= 0 and trade_action.units < 0:
            self.trade_cost = abs(trade_action.units) * trade_action.price
            self.outstanding = self.outstanding + self.trade_cost      
            self.trade_pl = 0      
            self.go_short = self.go_short + 1
            transaction = "Go Short - Sell"
            # logger.info(f"Go Short -- shares: {trade_action.units}, at price: {trade_action.price}, P&L {'${:,.2f}'.format(self.pl)}")
        elif self.have_units > 0 and trade_action.units < 0:
            self.trade_cost = abs(trade_action.units) * trade_action.price
            self.trade_pl = self.trade_cost - self.outstanding
            self.pl = self.pl + self.trade_pl
            self.close_long = self.close_long + 1
            self.outstanding = 0
            transaction = "Close Long - Sell" if not trade_action.sl_trade else "Close Long - Sell (SL)"
            # logger.info(f"Close Long -- shares: {trade_action.units}, at price: {trade_action.price}, P&L {'${:,.2f}'.format(self.pl)}")
        elif self.have_units < 0 and trade_action.units > 0:
            self.trade_cost = abs(trade_action.units) * trade_action.price
            self.trade_pl = self.outstanding - self.trade_cost
            self.pl = self.pl + self.trade_pl
            self.close_short = self.close_short + 1
            self.outstanding = 0
            transaction = "Close Short - Buy" if not trade_action.sl_trade else "Close Short - Buy (SL)"
            # logger.info(f"Close Short -- shares: {trade_action.units}, at price: {trade_action.price}, P&L {'${:,.2f}'.format(self.pl)}")
        
        self.have_units = self.have_units + trade_action.units
        self.trades.append([date_time.strftime("%m/%d/%Y %H:%M:%S"), trade_action.transaction, trade_action.price, '${:,.2f}'.format(self.trade_pl), kwargs.get("rsi"), kwargs.get("rsi_min"), kwargs.get("rsi_max"), '${:,.2f}'.format(self.pl)])

        return

    def print_trades(self):

        logger.info("\n" + 100 * "-")        
        logger.info("\n" + tabulate(self.trades, headers = self.columns))
        logger.info(f"Finished Trading Session with P&L: {'${:,.2f}'.format(self.pl)}, # of trades: {len(self.trades)}, have units: {self.have_units}")
        logger.info(f"go long: {self.go_long}, go short: {self.go_short}, close long: {self.close_long}, close short: {self.close_short}")
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