import argparse
import pandas as pd
import matplotlib.pyplot as plt
# Plan

# 1. Read a CSV file containing open fund data into a pandas DataFrame.
# the csv file include 3 cols
# an example showed below
# datetime,open,rate
# 2021-10-20,1.0,0.0
# 2021-10-22,0.9999,0.0
# 2021-10-26,0.9999,0.0
# 2021-10-27,0.9933,-0.66

def read_open_fund_csv(file_path: str):
    df = pd.read_csv(file_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    return df

def calc_windowed_revenue(df, window_days: int, price_column: str='open'):
    """
    Calculate revenue as last day price - first day price in the window.
    """
    rolling_revenue = df[price_column].rolling(f'{window_days}D').apply(lambda x: x.iloc[-1] - x.iloc[0])
    return rolling_revenue


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze open fund data: calculate revenues over fixed windows.')
    parser.add_argument('file_path', help='Path to the CSV file')
    parser.add_argument('--revenue_column', default='open', help='Column to calculate revenue on (default: open)')

    args = parser.parse_args()

    df = read_open_fund_csv(args.file_path)
    windows = [5, 14, 30, 90, 300]

    df_result = pd.DataFrame(index=df.index)

    for window in windows:
        revenue_series = calc_windowed_revenue(df, window, args.revenue_column)
        df_result[f'revenue_{window}d'] = revenue_series

    # Export to CSV
    output_file = args.file_path.replace('.csv', '_revenues.csv')
    df_result.to_csv(output_file)
    print(f"Revenue series for all windows exported to {output_file}")

    # Show distributions
    for window in windows:
        series = df_result[f'revenue_{window}d'].dropna()
        print(f"\nRevenue Distribution for {window}d window:")
        print(series.describe())

    # Plot time series
    plt.figure()
    for window in windows:
        df_result[f'revenue_{window}d'].plot(label=f'{window}d')
    plt.title('Windowed Revenues Over Time')
    plt.xlabel('Date')
    plt.ylabel('Revenue')
    plt.legend()
    ts_file = args.file_path.replace('.csv', '_revenues_ts.png')
    plt.savefig(ts_file)
    print(f"Time series plot saved to {ts_file}")

