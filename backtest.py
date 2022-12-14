from __future__ import print_function
import datetime
import pprint
import queue
import time
from dataclasses import dataclass,asdict,astuple,field
from data import DataHandler
from execution import ExecutionHandler
from portfolio import Portfolio 
from strategies.strategy import Strategy

@dataclass(order=True)
class Backtest(object):
    """
    Enscapsulates the settings and components for carrying out
    an event-driven backtest.
    """
    
    """
    Initialises the backtest.
    Parameters:
    csv_dir - The hard root to the CSV data directory.
    symbol_list - The list of symbol strings.
    intial_capital - The starting capital for the portfolio.
    heartbeat - Backtest "heartbeat" in seconds
    start_date - The start datetime of the strategy.
    data_handler - (Class) Handles the market data feed.
    execution_handler - (Class) Handles the orders/fills for trades.
    portfolio - (Class) Keeps track of portfolio current
    and prior positions.
    strategy - (Class) Generates signals based on market data.
    """
    
    csv_dir :str
    symbol_list : list 
    initial_capital : float
    heartbeat : float
    start_date : datetime.datetime
    data_handler_cls : DataHandler
    execution_handler_cls : ExecutionHandler
    portfolio_cls : Portfolio
    strategy_cls : Strategy
    events : queue.Queue = queue.Queue()
    signals : int = 0
    orders : int = 0
    fills : float = 0
    num_strats : int = 1
    
    def __post_init__(self):
        self._generate_trading_instances()
    def _generate_trading_instances(self):
        """
        Generates the trading instance objects from
        their class types.
        """
        print(
        "Creating DataHandler, Strategy, Portfolio and ExecutionHandler"
        )
        self.data_handler = self.data_handler_cls(self.events, self.csv_dir,
        self.symbol_list)
        self.strategy = self.strategy_cls(self.data_handler, self.events)
        self.portfolio = self.portfolio_cls(self.data_handler, self.events,
        self.start_date,
        self.initial_capital)
        self.execution_handler = self.execution_handler_cls(self.events)
    def _run_backtest(self):
        """
        Executes the backtest.
        """
        i = 0
        while True:
            i += 1
            print(i)
            # Update the market bars
            if self.data_handler.continue_backtest == True:
                self.data_handler.update_bars()
            else:
                break
            # Handle the events
            while True:
                try:
                    event = self.events.get(False)
                except queue.Empty:
                    break
                else:
                    if event is not None:
                        if event.type == 'MARKET':
                            self.strategy.calculate_signals(event)
                            self.portfolio.update_timeindex(event)
                        elif event.type == 'SIGNAL':
                            self.signals += 1
                            self.portfolio.update_signal(event)
                        elif event.type == 'ORDER':
                            self.orders += 1
                            self.execution_handler.execute_order(event)
                        elif event.type == 'FILL':
                            self.fills += 1
                            self.portfolio.update_fill(event)
            time.sleep(self.heartbeat)
    def _output_performance(self):
        """
        Outputs the strategy performance from the backtest.
        """
        self.portfolio.create_equity_curve_dataframe()
        print("Creating summary stats...")
        stats = self.portfolio.output_summary_stats()
        print("Creating equity curve...")
        print(self.portfolio.equity_curve.tail(10))
        pprint.pprint(stats)
        print("Signals: %s" % self.signals)
        print("Orders: %s" % self.orders)
        print("Fills: %s" % self.fills)
    
    def simulate_trading(self):
        """
        Simulates the backtest and outputs portfolio performance.
        """
        self._run_backtest()
        self._output_performance()