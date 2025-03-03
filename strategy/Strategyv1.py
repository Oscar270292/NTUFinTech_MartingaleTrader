import json
import pandas as pd
from datetime import datetime, timedelta
from market_conditionv1 import market_prediction
from Martingalev1 import martingale

def main():
    print("Start testing the strategy...")

    # Load parsed data from JSON file
    with open(r'data.json', 'r') as file:
        parsed_data = json.load(file)

    end_values = []
    sharpe_ratios = []
    trade = []
    last_entry_time = []

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
        end_value, sharpe_ratio, total_trades, last_entry = martingale(symbol, starting_date, result_date, market, capital)
        print(f"Market prediction for {symbol} starting on {start_date}: {market}, End Value = {end_value}, Sharpe Ratio = {sharpe_ratio}, trade = {total_trades}, last_entry = {last_entry}")

        # Append results
        end_values.append(end_value)
        sharpe_ratios.append(sharpe_ratio)
        trade.append(total_trades)
        last_entry_time.append(last_entry)
        n += 1
        if n == 180:
            print("Reached 180 iterations. Exiting loop.")
            break

    # Save results to CSV file
    results = {
        'symbol': list(parsed_data.values())[:n],
        'start_date': list(parsed_data.keys())[:n],
        'end_value': end_values,
        'sharpe_ratio': sharpe_ratios,
        'trade time': trade,
        'last_entry_time': last_entry_time
    }
    df = pd.DataFrame(results)
    output_file = 'results2_v1.csv'
    df.to_csv(output_file, index=False)
    print(f"Results saved to {output_file}")

if __name__ == '__main__':
    main()
