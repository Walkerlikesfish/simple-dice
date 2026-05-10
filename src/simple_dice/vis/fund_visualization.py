import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from simple_dice.data.processor import calc_revenue_window

# Mapping from window name to days
window_days = {'week': 5, 'month': 21, 'quarter': 63, 'half_year': 180, 'year': 360}


def load_fund_data_from_frame_dir(frame_dir, fund_code):
    """Load fund data from frame_dir for a given fund_code.
    
    Args:
        frame_dir: Directory path where fund CSV files are stored
        fund_code: Unique identifier for the fund
        
    Returns:
        DataFrame containing fund data or None if file not found
    """
    frame_path = os.path.join(frame_dir, f'{fund_code}.csv')
    if not os.path.exists(frame_path):
        print(f"Frame file not found for fund {fund_code}: {frame_path}")
        return None
    df = pd.read_csv(frame_path)
    return df


def plot_fund_with_window_extrema(fund_code, mark_windows=None, frame_dir=None):
    """Plot fund cumulative net value with window extrema marked.
    
    Args:
        fund_code: Unique identifier for the fund
        mark_windows: List of window sizes to mark (week, month, quarter, etc.)
        frame_dir: Directory path where fund CSV files are stored
    """
    if mark_windows is None:
        mark_windows = ['week', 'month', 'quarter']

    # Load fund data from frame_dir
    df = load_fund_data_from_frame_dir(frame_dir, fund_code)
    if df is None:
        print(f"Fund {fund_code} not found in frame_dir")
        return

    if 'datetime' not in df.columns or 'cum_net_value' not in df.columns:
        print("Data must contain 'datetime' and 'cum_net_value' columns")
        return

    # Prepare dataframe: parse dates and sort
    df['datetime'] = pd.to_datetime(df['datetime']).dt.normalize()
    df = df.sort_values('datetime').reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df['datetime'], df['cum_net_value'], label=f'cum_net_value {fund_code}', color='tab:blue')

    colors = {'week': 'C1', 'month': 'C2', 'quarter': 'C3', 'half_year': 'C4', 'year': 'C5'}
    markers = {'min': 'v', 'max': '^'}

    for w in mark_windows:
        if w not in window_days:
            print(f"Unknown window {w}, skipping")
            continue
        days = window_days[w]

        # Compute window returns aligned with this sorted df
        returns = calc_revenue_window(df, days, return_pct=True)

        if returns.dropna().empty:
            print(f"No valid returns for window {w} on fund {fund_code}")
            continue

        # locate min and max (positions correspond to df indices)
        min_pos = returns.idxmin()
        max_pos = returns.idxmax()

        # If idxmin/idxmax return NaN or are outside, skip
        if pd.isna(min_pos) or pd.isna(max_pos):
            continue

        # Get corresponding dates and cum_net_value
        min_date = df.loc[int(min_pos), 'datetime']
        min_val = df.loc[int(min_pos), 'cum_net_value']
        max_date = df.loc[int(max_pos), 'datetime']
        max_val = df.loc[int(max_pos), 'cum_net_value']

        # Plot markers
        ax.scatter([min_date], [min_val], color=colors.get(w, 'k'), marker=markers['min'], s=80, label=f'{w} min')
        ax.scatter([max_date], [max_val], color=colors.get(w, 'k'), marker=markers['max'], s=80, label=f'{w} max')

        # Annotate
        ax.annotate(f"{w} min\n{min_date.date()}\n{returns.loc[int(min_pos)]:.2%}",
                    xy=(min_date, min_val), xytext=(0, -40), textcoords='offset points',
                    ha='center', va='top', fontsize=8, color=colors.get(w, 'k'))

        ax.annotate(f"{w} max\n{max_date.date()}\n{returns.loc[int(max_pos)]:.2%}",
                    xy=(max_date, max_val), xytext=(0, 10), textcoords='offset points',
                    ha='center', va='bottom', fontsize=8, color=colors.get(w, 'k'))

    # Formatting
    ax.set_title(f'Fund {fund_code} cumulative net value with window extrema')
    ax.set_xlabel('Date')
    ax.set_ylabel('cum_net_value')
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.legend()
    plt.tight_layout()
    plt.show()
