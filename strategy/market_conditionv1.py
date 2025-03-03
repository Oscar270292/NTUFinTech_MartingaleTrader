import pandas as pd
from datetime import datetime, timedelta
from binance.client import Client

API_KEY = 'qQa7WaIwBvPswvAxAmahydHdUbMf4xBQylpUdo7lfW5RFqAqfmVUK6ItJRdTtDmj'
API_SECRET = 'uk56NAEgulocSm5rGJwKAZ7vnLtSxDRhPenxvRJWBFfXQO8PSkaoydbw0HSNhmGX'

client = Client(API_KEY, API_SECRET)

def fetch_binance_data(symbol, interval, start_date, end_date):
    klines = client.get_historical_klines(
        symbol=symbol,
        interval=interval,
        start_str=start_date,
        end_str=end_date,
        limit=1000
    )
    data = [
        {
            'datetime': datetime.fromtimestamp(kline[0] / 1000),
            'open': float(kline[1]),
            'high': float(kline[2]),
            'low': float(kline[3]),
            'close': float(kline[4]),
            'volume': float(kline[5]),
        }
        for kline in klines
    ]
    df = pd.DataFrame(data)
    df.set_index('datetime', inplace=True)
    return df

def calculate_indicators(df):
    df['SMA_5'] = df['close'].rolling(window=5).mean()
    df['TR'] = df[['high', 'low', 'close']].apply(
        lambda row: max(
            row['high'] - row['low'], 
            abs(row['high'] - row['close']), 
            abs(row['low'] - row['close'])
        ), axis=1
    )
    df['ATR'] = df['TR'].rolling(window=5).mean()
    return df


def predict_next_week_market(df, prediction_date):
    if prediction_date not in df.index:
        return "Insufficient data for prediction"

    sma_5 = df.loc[prediction_date, 'SMA_5']
    if isinstance(sma_5, pd.Series):
        sma_5 = sma_5.iloc[0]
    atr_mean = df['ATR'].mean()

    past_week = df.loc[:prediction_date].tail(7)
    past_close_mean = past_week['close'].mean()
    past_atr_mean = past_week['ATR'].mean()

    if past_atr_mean > atr_mean * 1.5:
        return "High Volatility"
    elif past_close_mean > sma_5 and past_atr_mean < atr_mean:
        return "Uptrend"
    elif past_close_mean < sma_5 and past_atr_mean > atr_mean:
        return "Downtrend"
    else:
        return "Ranging"

def market_prediction(symbol, start_date):
    interval = Client.KLINE_INTERVAL_1DAY
    target_datetime = datetime.strptime(start_date, '%Y-%m-%d')
    result_date = (target_datetime - timedelta(days=51)).strftime('%Y-%m-%d')

    df = fetch_binance_data(symbol, interval, result_date, start_date)
    df = calculate_indicators(df)
    return predict_next_week_market(df, start_date)

# Example usage:
# prediction = market_prediction('BTCUSDT', '2024-03-18')
# print(prediction)
