import argparse
import backtrader as bt
import datetime
import pandas as pd
from binance.client import Client
import pytz

API_KEY = ''
API_SECRET = ''

def fetch_binance_data(symbol, interval, start_date, end_date, timezone):
    client = Client(API_KEY, API_SECRET)
    klines = client.get_historical_klines(
        symbol=symbol,
        interval=interval,
        start_str=start_date,
        end_str=end_date
    )
    data = []
    for kline in klines:
        utc_time = datetime.datetime.fromtimestamp(kline[0] / 1000, tz=pytz.utc)
        local_time = utc_time.astimezone(pytz.timezone(timezone))
        data.append({
            'datetime': local_time,
            'open': float(kline[1]),
            'high': float(kline[2]),
            'low': float(kline[3]),
            'close': float(kline[4]),
            'volume': float(kline[5]),
        })
    
    df = pd.DataFrame(data)
    if df.isnull().values.any() or (df[['open', 'high', 'low', 'close']] == 0).any().any():
        raise ValueError("Data contains null or zero values, which is invalid for backtesting")
    return df.to_dict('records')

class ReverseMartingaleStrategy(bt.Strategy):
    params = (
        ('fixed_position_size_bool', False),
        ('start_position_size', 5),  # Initial position size is 5% of total capital
        ('reverse_mult', 2),        # Reverse multiplier for position size
        ('profit_threshold', 5),  # Loosened profit threshold for re-entry
    )

    def __init__(self):
        # Indicators
        self.atr = bt.indicators.ATR(self.data, period=5)
        self.macd = bt.indicators.MACD(self.data.close)
        self.current_unit_size = None
        self.add_position_count = 0
        self.entry_price = None
        self.last_entry_time = None  # 紀錄最後一次進場時間

    def next(self):
        current_time = self.data.datetime.datetime(0)
        # Determine position size
        if self.params.fixed_position_size_bool:
            self.current_unit_size = self.params.start_position_size
        else:
            self.current_unit_size = (self.broker.getvalue() * (self.params.start_position_size / 100)) / self.data.close[0]

        # Entry condition: MACD crossover
        if self.macd.macd[0] > self.macd.signal[0] and self.position.size <= 0:
            self.buy(size=self.current_unit_size)
            self.add_position_count = 0
            self.last_entry_time = current_time  # 更新進場時間
            self.entry_price = self.data.close[0]

        # Manage position if already in
        if self.position.size > 0:
            entry_price = self.position.price
            price_percent = (self.data.close[0] - entry_price) / entry_price * 100

            # Add position if profit threshold is met
            if price_percent >= self.params.profit_threshold:
                new_unit_size = self.position.size * self.params.reverse_mult
                if self.broker.getcash() > new_unit_size * self.data.close[0]:
                    self.buy(size=new_unit_size)
                    self.add_position_count += 1
                    self.last_entry_time = current_time  # 更新進場時間

class MultifactorMartingaleStrategy(bt.Strategy):
    params = (
        ('start_position_size', 5),  # Initial position size as a percentage of total capital
        ('loss_threshold', 5),     # Percentage drop to trigger additional positions
        ('reverse_mult', 2.0),       # Multiplier for each additional position
        ('max_add_positions', 8),    # Maximum number of additional positions
    )

    def __init__(self):
        # Indicators
        self.macd = bt.indicators.MACD(self.data.close)
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        self.entry_price = None
        self.add_position_count = 0
        self.last_entry_time = None  # 紀錄最後一次進場時間

    def next(self):
        current_time = self.data.datetime.datetime(0)
        if self.position.size == 0:  # Entry logic
            if self.macd.macd[0] > self.macd.signal[0] and self.rsi[0] < 40:
                current_unit_size = (self.broker.getvalue() * (self.params.start_position_size / 100)) / self.data.close[0]
                self.buy(size=current_unit_size)
                self.entry_price = self.data.close[0]
                self.add_position_count = 0
                self.last_entry_time = current_time  # 更新進場時間

        elif self.position.size > 0:  # Position management logic
            profit_percent = (self.data.close[0] - self.entry_price) / self.entry_price * 100

            # Add position logic
            if profit_percent <= -self.params.loss_threshold and self.add_position_count < self.params.max_add_positions:
                new_unit_size = self.position.size * self.params.reverse_mult
                if self.broker.getcash() > new_unit_size * self.data.close[0]:
                    self.buy(size=new_unit_size)
                    self.add_position_count += 1
                    self.last_entry_time = current_time  # 更新進場時間
class TimeLimitedMartingaleStrategy(bt.Strategy):
    params = (
        ('macd_fast', 12),  # Fast EMA period
        ('macd_slow', 26),  # Slow EMA period
        ('macd_signal', 9),  # Signal line period
        ('initial_risk_percent', 5),  # Initial entry position as percentage of capital
        ('martingale_factor', 2.0),  # Multiplier for additional positions
        ('add_threshold_percent', 5.0),  # Threshold for price drop to trigger additional positions
        ('max_add_positions', 8),  # Maximum number of additional positions
    )

    def __init__(self):
        # MACD Indicator
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.macd_fast,
            period_me2=self.params.macd_slow,
            period_signal=self.params.macd_signal
        )
        self.current_unit_size = None
        self.entry_price = None
        self.add_position_count = 0  # Number of additional positions taken
        self.last_entry_time = None  # 紀錄最後一次進場時間

    def next(self):
        current_time = self.data.datetime.datetime(0)
        # Entry condition: MACD crossover
        if not self.position and self.macd.macd[0] > self.macd.signal[0]:
            self.current_unit_size = (self.broker.getvalue() * (self.params.initial_risk_percent / 100)) / self.data.close[0]
            self.buy(size=self.current_unit_size)
            self.entry_price = self.data.close[0]
            self.add_position_count = 0
            self.last_entry_time = current_time  # 更新進場時間

        # Add position logic
        elif self.position.size > 0:
            price_drop = (self.entry_price - self.data.close[0]) / self.entry_price * 100

            if price_drop >= self.params.add_threshold_percent and self.add_position_count < self.params.max_add_positions:
                # Increase the position size using martingale factor
                new_unit_size = self.position.size * self.params.martingale_factor
                if self.broker.getcash() > new_unit_size * self.data.close[0]:
                    self.buy(size=new_unit_size)
                    self.add_position_count += 1
                    self.last_entry_time = current_time  # 更新進場時間
                    self.entry_price = self.data.close[0]
class RiskLimitedMartingaleStrategy(bt.Strategy):
    params = (
        ('fixed_position_size', False),  # Whether to use fixed position size
        ('start_position_size', 0.5),    # Reduced initial position size to conserve capital
        ('initial_risk_percent', 5),  # Increased initial position percentage
        ('martingale_factor', 2.0),     # Multiplier for additional positions
        ('add_threshold_percent', 5.0), # Loosened add threshold percentage
        ('max_add_positions', 8),       # Maximum number of additional positions
    )

    def __init__(self):
        self.current_unit_size = None
        self.add_position_count = 0  # Tracks the number of additional positions
        self.macd = bt.indicators.MACD(self.data.close)
        self.entry_price = None  # Tracks the initial entry price
        self.last_entry_time = None  # 紀錄最後一次進場時間

    def next(self):
        current_time = self.data.datetime.datetime(0)
        # Entry logic
        if not self.position:  # No current position
            if self.macd.macd[0] > self.macd.signal[0]:  # MACD crossover signal
                if self.params.fixed_position_size:
                    self.current_unit_size = self.params.start_position_size
                else:
                    self.current_unit_size = (self.broker.getvalue() * (self.params.initial_risk_percent / 100)) / self.data.close[0]
                self.buy(size=self.current_unit_size)
                self.entry_price = self.data.close[0]
                self.add_position_count = 0
                self.last_entry_time = current_time  # 更新進場時間

        # Add position logic
        elif self.position.size > 0:
            price_drop = (self.position.price - self.data.close[0]) / self.position.price * 100
            if price_drop >= self.params.add_threshold_percent and self.add_position_count < self.params.max_add_positions:

                new_unit_size = self.position.size * self.params.martingale_factor
                if self.broker.getcash() >= new_unit_size * self.data.close[0]:
                    self.buy(size=new_unit_size)
                    self.add_position_count += 1
                    self.last_entry_time = current_time  # 更新進場時間
                    self.entry_price = self.data.close[0]  # Update entry price after adding position
            

strategies = {
    "reverse": ReverseMartingaleStrategy,
    "multifactor": MultifactorMartingaleStrategy,
    "time_limited": TimeLimitedMartingaleStrategy,
    "risk_limited": RiskLimitedMartingaleStrategy,
}

market_strategies = {
    "Uptrend": ReverseMartingaleStrategy,
    "Ranging": MultifactorMartingaleStrategy,
    "High Volatility": TimeLimitedMartingaleStrategy,
    "Downtrend": RiskLimitedMartingaleStrategy,
}

def martingale(symbol, start_date, end_date, market_condition, capital):

    timezone = 'UTC'
    interval = Client.KLINE_INTERVAL_1MINUTE  # 1 分鐘 K 線


    # Fetch Binance data
    raw_data = fetch_binance_data(symbol, interval, start_date, end_date, timezone)

    # Load data into backtrader
    class BinanceData(bt.feeds.PandasData):
        params = (
            ('datetime', 'datetime'),
            ('open', 'open'),
            ('high', 'high'),
            ('low', 'low'),
            ('close', 'close'),
            ('volume', 'volume')
        )

    df = pd.DataFrame(raw_data)
    data = BinanceData(dataname=df)

    # Create backtesting engine
    cerebro = bt.Cerebro()

    # Add chosen strategy
    strategy = market_strategies[market_condition]
    cerebro.addstrategy(strategy)

    # Add data
    cerebro.adddata(data)

    # Configure initial capital
    cerebro.broker.set_cash(capital)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", timeframe=bt.TimeFrame.Days, annualize=True)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trade_analyzer")  # 用於計算交易次數

    # Run backtest
    results = cerebro.run()

    sharpe_analyzer = results[0].analyzers.sharpe
    buy_count = results[0].add_position_count + 1  # 自定義屬性，從策略中取得
    last_entry = results[0].last_entry_time  # 紀錄最後一次進場時間
    #cerebro.plot()
    return cerebro.broker.getvalue(), sharpe_analyzer.get_analysis().get('sharperatio', 'N/A'), buy_count, last_entry
