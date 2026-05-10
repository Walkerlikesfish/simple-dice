"""VectorBT Data class backed by AKShare open fund data.

Usage:
    data = AKFundData.download(
        ['161017', '000001'],
        start='2024-01-01',
        end='2024-12-31',
        cache_dir='/path/to/frame_cum',
    )
    price = data.get('Close')
    pf = vbt.Portfolio.from_holding(price, init_cash=100_000)

Fee post-processing (approach D):
    adj_returns = adjust_for_fund_fees(pf.trades)
"""

import os
from datetime import datetime, timedelta

import akshare as ak
import pandas as pd
import vectorbt as vbt

# Default cache location used by the legacy script
default_frame_dir = '/Users/yuliu/Documents/workspace/data/dice_data/open_fund/frame_cum/'


class AKFundData(vbt.Data):
    """VectorBT Data source for Chinese open-end funds via AKShare.

    Caches downloaded data on disk. Falls back to AKShare API on cache miss
    or when the cached file is older than ``ttl_hours``.
    """

    @classmethod
    def download_symbol(
        cls,
        symbol,
        start=None,
        end=None,
        cache_dir=None,
        ttl_hours=6,
        **kwargs,
    ):
        """Download a single fund's historical accumulated net value.

        Parameters
        ----------
        symbol : str
            Fund code, e.g. '161017'. Will be zero-padded to 6 digits.
        start : str or datetime, optional
            Start date (inclusive).
        end : str or datetime, optional
            End date (inclusive).
        cache_dir : str, optional
            Directory to read/write cached CSV files.
            Defaults to the legacy hard-coded path.
        ttl_hours : int, default 6
            Cache time-to-live. If the cached file is older than this,
            re-fetch from AKShare.
        **kwargs
            Ignored (absorbed for compatibility).

        Returns
        -------
        pd.DataFrame
            DataFrame with DatetimeIndex and columns:
            ['Open', 'High', 'Low', 'Close', 'Volume'].
            Close is the accumulated net value (累计净值).
        """
        symbol = str(symbol).zfill(6)
        cache_dir = cache_dir or default_frame_dir
        cache_path = os.path.join(cache_dir, f'{symbol}.csv')

        # --- Load from cache if fresh ----------------------------------------
        df = None
        if os.path.exists(cache_path):
            mtime = datetime.fromtimestamp(os.path.getmtime(cache_path))
            if datetime.now() - mtime < timedelta(hours=ttl_hours):
                df = pd.read_csv(cache_path, encoding='utf-8')

        # --- Fetch from AKShare if needed ------------------------------------
        if df is None:
            try:
                raw = ak.fund_open_fund_info_em(symbol=symbol, indicator="累计净值走势")
                raw = raw.rename(columns={'净值日期': 'datetime', '累计净值': 'cum_net_value'})
                df = raw[['datetime', 'cum_net_value']].copy()
                df['datetime'] = pd.to_datetime(df['datetime'])

                # Persist to cache
                os.makedirs(cache_dir, exist_ok=True)
                df.to_csv(cache_path, index=False, encoding='utf-8')
            except Exception as exc:
                # If AKShare fails but we have a stale cache, use it as fallback
                if os.path.exists(cache_path):
                    df = pd.read_csv(cache_path, encoding='utf-8')
                else:
                    raise RuntimeError(
                        f"Failed to fetch {symbol} from AKShare and no cache exists."
                    ) from exc

        # --- Normalise index -------------------------------------------------
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.set_index('datetime').sort_index()

        # --- Date filter ------------------------------------------------------
        if start is not None:
            df = df[df.index >= pd.to_datetime(start)]
        if end is not None:
            df = df[df.index <= pd.to_datetime(end)]

        # --- Map to OHLCV -----------------------------------------------------
        # Funds only publish one price per day (accumulated net value).
        # We synthesise OHLC so vectorbt is happy.
        out = pd.DataFrame(index=df.index)
        out['Close'] = df['cum_net_value'].astype(float)
        out['Open'] = out['Close'].shift(1)
        out['Open'] = out['Open'].fillna(out['Close'])  # first row
        out['High'] = out['Close']
        out['Low'] = out['Close']
        out['Volume'] = 0

        return out


def adjust_for_fund_fees(trades, short_term_rate=0.015, mid_term_rate=0.005):
    """Post-process vectorbt trades to account for tiered fund redemption fees.

    This implements **approach D**: adjust returns *after* backtesting instead
    of trying to bake holding-period fees into vectorbt's flat-fee model.

    Parameters
    ----------
    trades : vectorbt.trades accessor
        Usually ``pf.trades``.
    short_term_rate : float, default 0.015
        Redemption fee for holdings < 7 days.
    mid_term_rate : float, default 0.005
        Redemption fee for holdings 7–30 days.

    Returns
    -------
    pd.DataFrame
        Copy of the trade records with added columns:
        ``hold_days``, ``fee_rate``, ``adj_return``, ``adj_pnl``.
    """
    records = trades.records.copy()
    if records is None or len(records) == 0:
        return records

    # Holding period in bars (= days for daily data)
    records['hold_days'] = records['exit_idx'] - records['entry_idx']

    # Tiered fee rate
    records['fee_rate'] = 0.0
    records.loc[records['hold_days'] < 7, 'fee_rate'] = short_term_rate
    records.loc[(records['hold_days'] >= 7) & (records['hold_days'] < 30), 'fee_rate'] = mid_term_rate

    # Adjust percentage return
    records['adj_return'] = records['return'] - records['fee_rate']

    # Adjust absolute PnL (fee applied to exit notional value)
    records['adj_pnl'] = records['pnl'] - records['size'] * records['exit_price'] * records['fee_rate']

    return records
