import os
import argparse
import numpy as np
import akshare as ak
import matplotlib.pyplot as plt
import pandas as pd
from tqdm import tqdm

from simple_dice.data.processor import calc_revenue_window


def load_all_funds(frame_index_file, frame_dir):
    frame_index_df = pd.read_csv(frame_index_file, dtype={'fund_code': str})
    all_funds_data = {}
    for fund_code in frame_index_df['基金代码'].unique():
        fund_code = str(fund_code).zfill(6)
        fund_file = os.path.join(frame_dir, f'{fund_code}.csv')
        if os.path.exists(fund_file):
            try:
                fund_df = pd.read_csv(fund_file, encoding='utf-8')
                if not fund_df.empty:
                    all_funds_data[str(fund_code)] = fund_df
            except Exception as e:
                print(f"Error reading fund {fund_code}: {e}")
                continue
    return all_funds_data


def compute_fund_yields(task):
    """Worker function to compute yields for one fund.
    `task` is a tuple (fund_code, fund_df, window_configs, annualize_returns)
    Returns (fund_code, results_dict) or (fund_code, None) on error/empty.
    """
    fund_code, fund_df, window_configs, annualize_returns = task
    try:
        if fund_df.empty or 'cum_net_value' not in fund_df.columns:
            return fund_code, None

        res = {}
        for window_name, config in window_configs.items():
            window_size = config['days']
            annualization_factor = config['annualization_factor']

            windowed_returns = calc_revenue_window(fund_df, window_size, return_pct=True)
            windowed_returns = windowed_returns.dropna()
            if len(windowed_returns) == 0:
                continue

            factor = annualization_factor if annualize_returns else 1
            std_factor = np.sqrt(annualization_factor) if (annualize_returns and annualization_factor > 0) else 1

            mean_val = windowed_returns.mean()
            std_val = windowed_returns.std()

            res[window_name] = {
                'mean': mean_val * factor,
                'std': std_val * std_factor,
                'min': windowed_returns.min() * factor,
                'max': windowed_returns.max() * factor,
                'p25': windowed_returns.quantile(0.25) * factor,
                'p50': windowed_returns.quantile(0.50) * factor,
                'p75': windowed_returns.quantile(0.75) * factor,
                'count': len(windowed_returns)
            }

        return fund_code, res
    except Exception as e:
        print(f"Error computing yields for {fund_code}: {e}")
        return fund_code, None


def aggregate_results(results_iter):
    annual_yields = {}
    for fund_code, res in results_iter:
        if res:
            annual_yields[fund_code] = res
    return annual_yields


def main():
    # Setup argument parser
    parser = argparse.ArgumentParser(description='Process fund data and calculate windowed revenue returns.')
    parser.add_argument('--data_dir', type=str, default='/Users/yuliu/Documents/workspace/data/dice_data/open_fund/',
                        help='Base data directory (default: /Users/yuliu/Documents/workspace/data/dice_data/open_fund/)')
    parser.add_argument('--frame_index_file', type=str, default=None,
                        help='Path to fund index CSV file (default: {data_dir}/all_fund_index.csv)')
    parser.add_argument('--frame_dir', type=str, default=None,
                        help='Directory containing fund data CSVs (default: {data_dir}/frame_cum/)')
    parser.add_argument('--stats_dir', type=str, default=None,
                        help='Directory to save stats (default: {data_dir}/stats/)')
    parser.add_argument('--output_path', type=str, default=None,
                        help='Output path for annual_yields_df CSV (default: {stats_dir}/annual_yields.csv)')
    parser.add_argument('--annualize_returns', action='store_true', default=False,
                        help='Enable annualization of returns (default: False)')
    parser.add_argument('--debug_limit', type=int, default=None,
                        help='Limit number of funds to process for debugging (default: None for all)')

    args = parser.parse_args()

    # Set default paths based on data_dir
    if args.frame_index_file is None:
        args.frame_index_file = os.path.join(args.data_dir, 'all_fund_index.csv')
    if args.frame_dir is None:
        args.frame_dir = os.path.join(args.data_dir, 'frame_cum/')
    if args.stats_dir is None:
        args.stats_dir = os.path.join(args.data_dir, 'stats/')
    if args.output_path is None:
        args.output_path = os.path.join(args.stats_dir, 'annual_yields.csv')

    # Ensure stats_dir exists
    os.makedirs(args.stats_dir, exist_ok=True)

    print(f"Processing with:")
    print(f"  data_dir: {args.data_dir}")
    print(f"  frame_index_file: {args.frame_index_file}")
    print(f"  frame_dir: {args.frame_dir}")
    print(f"  stats_dir: {args.stats_dir}")
    print(f"  output_path: {args.output_path}")
    print(f"  annualize_returns: {args.annualize_returns}")
    print(f"  debug_limit: {args.debug_limit}")

    # Read funds
    all_funds_data = load_all_funds(args.frame_index_file, args.frame_dir)
    print(f"Successfully loaded {len(all_funds_data)} funds")

    # Define window configurations
    window_configs = {
        'week': {'days': 5, 'annualization_factor': 252 / 5},
        'month': {'days': 21, 'annualization_factor': 252 / 21},
        'quarter': {'days': 63, 'annualization_factor': 252 / 63},
        'half_year': {'days': 126, 'annualization_factor': 252 / 126},
        'year': {'days': 252, 'annualization_factor': 1}
    }

    # Prepare tasks
    tasks = []
    for idx, (fund_code, fund_df) in enumerate(all_funds_data.items()):
        if args.debug_limit and idx >= args.debug_limit:
            break
        tasks.append((fund_code, fund_df, window_configs, args.annualize_returns))

    # Multiprocessing
    from concurrent.futures import ProcessPoolExecutor, as_completed

    results = []
    workers = args.workers if hasattr(args, 'workers') and args.workers else None
    max_workers = workers or min(32, (os.cpu_count() or 1))
    print(f"Running computation with up to {max_workers} workers")

    with ProcessPoolExecutor(max_workers=max_workers) as exe:
        futures = {exe.submit(compute_fund_yields, t): t[0] for t in tasks}
        for fut in tqdm(as_completed(futures), total=len(futures)):
            fund_code, res = fut.result()
            results.append((fund_code, res))

    annual_yields = aggregate_results(results)

    print(f"Calculated annual yields for {len(annual_yields)} funds (annualize_returns={args.annualize_returns})")

    # Convert to DataFrame for easier analysis
    annual_yields_data = []
    for fund_code, windows in annual_yields.items():
        for window_name, stats in windows.items():
            row = {'fund_code': fund_code, 'window': window_name}
            row.update(stats)
            annual_yields_data.append(row)

    annual_yields_df = pd.DataFrame(annual_yields_data)
    print(f"Annual yields summary (shape: {annual_yields_df.shape}):")
    print(annual_yields_df.head(10))

    # Save to output path
    os.makedirs(os.path.dirname(args.output_path) or '.', exist_ok=True)
    annual_yields_df.to_csv(args.output_path, index=False, encoding='utf-8')
    print(f"Saved annual_yields_df to {args.output_path}")


if __name__ == '__main__':
    main()
