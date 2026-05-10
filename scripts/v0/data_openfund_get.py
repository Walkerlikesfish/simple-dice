import os
import sys
import argparse
import akshare as ak
import pandas as pd
from tqdm import tqdm
from multiprocessing import Pool
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

mainpath = os.path.dirname(os.path.dirname(__file__))
DIR_DATA = '/Users/yuliu/Documents/workspace/data/dice_data/open_fund/'
META_DIR = os.path.join(DIR_DATA, 'meta/')
FRAME_DIR = os.path.join(DIR_DATA, 'frame_cum/')
os.makedirs(DIR_DATA, exist_ok=True)
os.makedirs(META_DIR, exist_ok=True)
os.makedirs(FRAME_DIR, exist_ok=True)


def get_all_fund_list(enforce=False, save_path=os.path.join(DIR_DATA, f'all_fund_index.csv')):
    """Get all open fund list
    """
    if os.path.exists(save_path) and not enforce:
        print(f"File {save_path} exists, skip downloading.")
        return
    fund_em_fund_name_df = ak.fund_name_em()
    fund_em_fund_name_df.to_csv(save_path, index=None, encoding='utf-8')


def get_open_fund_meta_info(fund_code, save_path=None):
    """Get single open fund meta info
    """
    # for fund_code, if it is integer, convert to str with leading zeros to pad to length 6
    fund_code = str(fund_code).zfill(6)
    if os.path.exists(save_path) and save_path is not None:
        print(f"File {save_path} exists, skip downloading.")
        return pd.read_csv(save_path, encoding='utf-8')
    try:
        fund_data = ak.fund_individual_basic_info_xq(symbol=fund_code)
        if save_path:
            fund_data.to_csv(save_path, index=None, encoding='utf-8')
    except Exception as e:
        print(f"Error fetching fund data for {fund_code}: {e}")
        fund_data = None
    return fund_data


def fetch_fund_meta_wrapper(args):
    """Wrapper function for parallel processing"""
    fund_code, save_path = args
    return get_open_fund_meta_info(fund_code, save_path=save_path)


def get_open_fund_info(fund_code, use_acc=True, verbose=False):
    """Get single open fund info with datetime, open, rate columns
    """
    try:
        fund_code = str(fund_code).zfill(6)
        tar_save_path = os.path.join(FRAME_DIR, f'{fund_code}.csv')
        if os.path.exists(tar_save_path):
            if verbose: logging.info(f"File for {fund_code} exists, skip downloading.")
            return fund_code
        if use_acc:
            fund_data = ak.fund_open_fund_info_em(symbol=fund_code, indicator="累计净值走势")
            fund_data_new = fund_data.rename(columns={
                '净值日期': 'datetime',
                '累计净值': 'cum_net_value',
            })
            result_data = fund_data_new[['datetime', 'cum_net_value']]
        else:
            fund_data = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            fund_data_new = fund_data.rename(columns={
                '净值日期': 'datetime',
                '单位净值': 'open',
                '日增长率': 'rate',
            })
            result_data = fund_data_new[['datetime', 'open', 'rate']]
        result_data.to_csv(tar_save_path, index=None, encoding='utf-8')
        if verbose: logging.info(f"Successfully downloaded {fund_code}")
        return fund_code
    except Exception as e:
        if verbose: logging.error(f"Error fetching fund info for {fund_code}: {e}")
        return None


def init_database(get_meta=False):
    """
    Initialize the open fund database by fetching all fund info
    Run this once to populate the database
    """
    # Get all fund list
    idx_path = os.path.join(DIR_DATA, f'all_fund_index.csv')
    get_all_fund_list(enforce=False, save_path=idx_path)
    full_idx_df = pd.read_csv(idx_path, encoding='utf-8', index_col=0)
    full_idx_df.columns = ['code', 'py_abbr', 'fund_name', 'fund_cat', 'py_full']
    
    # Drop categories with less than 10 funds
    cat_counts = full_idx_df['fund_cat'].value_counts()
    valid_cats = cat_counts[cat_counts >= 10].index
    full_idx_df = full_idx_df[full_idx_df['fund_cat'].isin(valid_cats)]
    logging.info(f"Processing {len(full_idx_df)} funds across {len(valid_cats)} categories")
    
    # # Get meta info for each fund in parallel
    if get_meta:
        meta_args = []
        for _, row in full_idx_df.iterrows():
            fund_code = row['code']
            meta_save_path = os.path.join(META_DIR, f'{fund_code}_meta.csv')
            meta_args.append((fund_code, meta_save_path))
        with Pool(processes=8) as pool:
            list(tqdm(pool.imap_unordered(fetch_fund_meta_wrapper, meta_args), total=len(meta_args), desc="Fetching fund meta info"))

    # Get open fund info for each fund
    fund_codes = full_idx_df['code'].tolist()
    with Pool(processes=8) as pool:
        results = list(tqdm(pool.imap_unordered(get_open_fund_info, fund_codes), total=len(fund_codes), desc="Fetching fund info"))
    
    logging.info(f"Completed processing {len([r for r in results if r])} funds successfully")


def daily_update(idx_path=os.path.join(DIR_DATA, 'all_fund_index.csv'), frame_dir=FRAME_DIR):
    """
    Daily update of the open fund database
    """
    # Get existing fund list from index
    if not os.path.exists(idx_path):
        logging.error(f"Fund index not found at {idx_path}. Please run init_database first.")
        return
    
    full_idx_df = pd.read_csv(idx_path, encoding='utf-8', index_col=0)
    full_idx_df.columns = ['code', 'py_abbr', 'fund_name', 'fund_cat', 'py_full']
    
    # Drop categories with less than 10 funds
    cat_counts = full_idx_df['fund_cat'].value_counts()
    valid_cats = cat_counts[cat_counts >= 10].index
    full_idx_df = full_idx_df[full_idx_df['fund_cat'].isin(valid_cats)]
    
    # Update open fund info for each fund
    fund_codes = full_idx_df['code'].tolist()
    logging.info(f"Starting daily update for {len(fund_codes)} funds")
    fund_open_fund_daily_em_df = ak.fund_open_fund_daily_em()
    # The return of the function is a DataFrame containing daily data for all funds, below is an example
    # 	基金代码	基金简称	2026-01-29-单位净值	2026-01-29-累计净值	2026-01-28-单位净值	2026-01-28-累计净值	日增长值	日增长率	申购状态	赎回状态	手续费
    # 0	161725	招商中证白酒指数(LOF)A	0.7386	2.4547	0.6763	2.3924	0.0623	9.21	限大额	开放赎回	0.10%
    # 1	012414	招商中证白酒指数(LOF)C	0.7353	0.8203	0.6733	0.7583	0.062	9.21	限大额	开放赎回	0.00%
    # 2	009940	格林稳健价值混合A	0.5872	0.5872	0.5377	0.5377	0.0495	9.21	开放申购	开放赎回	0.15%
    # 3	009941	格林稳健价值混合C	0.575	0.575	0.5265	0.5265	0.0485	9.21	开放申购	开放赎回	0.00%
    # TODO: update each fund's data based on the new daily data, update by 累计净值 and take reference from date
    # Read each fund's existing data from `frame_dir` and append new data from the fund_open_fund_daily_em_df if available
    
    # Extract date from the most recent daily data column (format: "YYYY-MM-DD-累计净值")
    value_cols = [col for col in fund_open_fund_daily_em_df.columns if '累计净值' in col and col != '累计净值']
    if not value_cols:
        logging.warning("No new daily data available for update")
        return
    
    # Get the latest date from column names (they're in format "YYYY-MM-DD-累计净值")
    latest_date = value_cols[0].split('-')[0:3]  # Extract YYYY, MM, DD
    latest_date_str = '-'.join(latest_date)
    latest_value_col = value_cols[0]

    # Filter to only valid funds
    # Convert fund_codes to a set for faster lookup
    fund_codes_set = set([str(code).zfill(6) for code in fund_codes])
    fund_open_fund_daily_em_df['fund_code_normalized'] = fund_open_fund_daily_em_df['基金代码'].astype(str).str.zfill(6)
    fund_open_fund_daily_em_df = fund_open_fund_daily_em_df[fund_open_fund_daily_em_df['fund_code_normalized'].isin(fund_codes_set)]
    
    if len(fund_open_fund_daily_em_df) == 0:
        logging.warning(f"No matching funds found in daily data. Available fund codes: {fund_open_fund_daily_em_df['基金代码'].unique()[:10].tolist() if '基金代码' in fund_open_fund_daily_em_df.columns else 'N/A'}")
        return
    
    # Update each fund's data
    updated_count = 0
    logging.info(f"Updating fund data for {len(fund_open_fund_daily_em_df)} funds")
    for idx, row in tqdm(fund_open_fund_daily_em_df.iterrows(), total=len(fund_open_fund_daily_em_df), desc="Updating fund data"):
        fund_code = row['fund_code_normalized']
        tar_file_path = os.path.join(frame_dir, f'{fund_code}.csv')
        
        try:
            # Get the cumulative net value from the latest data
            cum_net_value = row[latest_value_col]
            
            # Skip if value is NaN
            if pd.isna(cum_net_value):
                continue
            
            # Read existing data
            if os.path.exists(tar_file_path):
                existing_df = pd.read_csv(tar_file_path, encoding='utf-8')
                
                # Check if this date already exists
                if latest_date_str in existing_df['datetime'].values:
                    logging.debug(f"Fund {fund_code} already has data for {latest_date_str}")
                    continue
                
                # Append new data
                new_row = pd.DataFrame({
                    'datetime': [latest_date_str],
                    'cum_net_value': [cum_net_value]
                })
                updated_df = pd.concat([existing_df, new_row], ignore_index=True)
            else:
                # Create new file with single row
                updated_df = pd.DataFrame({
                    'datetime': [latest_date_str],
                    'cum_net_value': [cum_net_value]
                })
            
            # Save updated data
            updated_df.to_csv(tar_file_path, index=None, encoding='utf-8')
            updated_count += 1
            
        except Exception as e:
            logging.error(f"Error updating fund {fund_code}: {e}")
            continue
    
    logging.info(f"Completed daily update: {updated_count} funds updated with new data")


def main():
    """Main entry point with CLI argument parsing"""
    parser = argparse.ArgumentParser(
        description='Open Fund Data Manager - Download and update open fund data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
            Examples:
            # Initialize database with fund data
            python data_openfund_get.py init --with-meta
            
            # Initialize database without meta info
            python data_openfund_get.py init
            
            # Daily update of fund data
            python data_openfund_get.py update
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    subparsers.required = True
    
    # Init database command
    init_parser = subparsers.add_parser('init', help='Initialize the open fund database')
    init_parser.add_argument(
        '--with-meta',
        action='store_true',
        help='Also fetch meta information for each fund (slower)'
    )
    
    # Daily update command
    update_parser = subparsers.add_parser('update', help='Daily update of the open fund database')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'init':
            logging.info("Starting database initialization...")
            init_database(get_meta=args.with_meta)
            logging.info("Database initialization completed successfully")
        elif args.command == 'update':
            logging.info("Starting daily update...")
            daily_update()
            logging.info("Daily update completed successfully")
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
