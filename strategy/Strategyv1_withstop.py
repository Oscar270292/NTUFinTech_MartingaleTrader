import json
import pandas as pd
from datetime import datetime, timedelta
from market_conditionv1 import market_prediction
from Martingalev1_withstop import martingale_withstop

def main():
    print("Start testing the strategy...")

    # Load parsed data from JSON file
    with open(r'data.json', 'r') as file:
        parsed_data = json.load(file)

    end_values = []
    max_drawdowns = []
    trade = []
    last_entry_time = []
    close = []

    # Loop through each entry in the JSON data
    n = 0
    for start_date, symbol in parsed_data.items():
        target_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        result_date = (target_datetime + timedelta(days=31)).strftime('%Y-%m-%d')
        starting_date = (target_datetime + timedelta(days=1)).strftime('%Y-%m-%d')

        # Predict market condition
        market = market_prediction(symbol, start_date)

        # Run the martingale strategy
        capital = 1000
        end_value, max_drawdown, total_trades, last_entry, close_time = martingale_withstop(symbol, starting_date, result_date, market, capital)
        print(f"Market prediction for {symbol} starting on {start_date}: {market}, End Value = {end_value}, max_drawdown = {max_drawdown}, trade = {total_trades}, last_entry = {last_entry}, close = {close_time}")

        # Append results
        end_values.append(end_value)
        max_drawdowns.append(max_drawdown)
        trade.append(total_trades)
        last_entry_time.append(last_entry)
        close.append(close_time)

    # Save results to CSV file
    results = {
        'symbol': list(parsed_data.values()),
        'start_date': list(parsed_data.keys()),
        'end_value': end_values,
        'max_drawdown': max_drawdowns,
        'trade time': trade,
        'last_entry_time': last_entry_time,
        'close_time': close
    }
    df = pd.DataFrame(results)
    output_file = 'results7_v1_withstop.csv'
    df.to_csv(output_file, index=False)
    print(f"Results saved to {output_file}")

if __name__ == '__main__':
    main()
