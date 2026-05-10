import pandas as pd
import numpy as np

# Define calc_revenue_window function for this calculation
def calc_revenue_window(per_fund_rec, t_win:int, return_pct:bool = True):
    """
    Calculate revenue (absolute or percentage) over a time window using datetime reference.
    Returns NaN if exact target date is not found. Vectorized for efficiency.
    
    Args:
        per_fund_rec (pd.DataFrame): DataFrame with columns 'datetime' and 'cum_net_value'
        t_win (int): Window size in days
        return_pct (bool): If True, return percentage return; if False, return absolute difference
    
    Returns:
        pd.Series: Revenue/return values for each row, or np.nan if target date not found or values are invalid
    """
    # Ensure datetime column is in datetime format
    per_fund_rec = per_fund_rec.copy()
    per_fund_rec['datetime'] = pd.to_datetime(per_fund_rec['datetime']).dt.normalize()
    per_fund_rec = per_fund_rec.sort_values('datetime').reset_index(drop=True)
    
    # Create a mapping of dates to indices for fast lookup
    date_to_idx = {date: idx for idx, date in enumerate(per_fund_rec['datetime'])}
    
    # Calculate all target dates vectorized
    current_dates = per_fund_rec['datetime'].values
    target_dates = current_dates - np.timedelta64(t_win, 'D')
    
    # Convert to pandas Series for easier indexing
    current_dates_pd = pd.Series(current_dates)
    target_dates_pd = pd.Series(target_dates)
    
    # Find indices for target dates (vectorized using map)
    start_indices = target_dates_pd.map(lambda d: date_to_idx.get(pd.Timestamp(d), np.nan))
    
    # Initialize revenue array
    revenues = np.full(len(per_fund_rec), np.nan)
    
    # Valid mask: where target date exists
    valid_mask = start_indices.notna()
    
    if valid_mask.any():
        # Get indices
        start_idx_arr = start_indices[valid_mask].astype(int).values
        end_idx_arr = np.where(valid_mask)[0]
        
        # Get values
        v_start = per_fund_rec.loc[start_idx_arr, 'cum_net_value'].values
        v_end = per_fund_rec.loc[end_idx_arr, 'cum_net_value'].values
        
        # Handle NaN values and invalid start values
        valid_values_mask = (~np.isnan(v_start)) & (~np.isnan(v_end)) & (v_start > 0 if return_pct else True)
        
        # Calculate revenue for valid entries
        if return_pct:
            calc_revenue = (v_end - v_start) / v_start
        else:
            calc_revenue = v_end - v_start
        
        # Place results only where valid
        revenues[end_idx_arr[valid_values_mask]] = calc_revenue[valid_values_mask]
    
    return pd.Series(revenues, index=per_fund_rec.index)
