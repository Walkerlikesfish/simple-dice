"""Demo: VectorBT backtesting with AKShare open fund data.

Usage:
    conda run -n py311 python scripts/v0/demo_vectorbt_akshare.py
"""

import os
import sys

import vectorbt as vbt

# Make sure the package is importable even if not pip-installed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from simple_dice.data.akshare_data import AKFundData, adjust_for_fund_fees

# ---------------------------------------------------------------------------
# 1. Download data
# ---------------------------------------------------------------------------
print("Downloading fund data...")
data = AKFundData.download(
    ['161017'],            # Fund code(s)
    start='2024-01-01',
    end='2025-12-31',
)

close = data.get('Close')
print(f"Loaded {len(close)} rows for {close.name}")
print(close.head())

# ---------------------------------------------------------------------------
# 2. Simple buy-and-hold backtest
# ---------------------------------------------------------------------------
print("\nRunning buy-and-hold backtest...")
pf = vbt.Portfolio.from_holding(close, init_cash=100_000)
print(pf.stats())

# ---------------------------------------------------------------------------
# 3. SMA crossover strategy
# ---------------------------------------------------------------------------
print("\nRunning SMA crossover backtest...")
fast_ma = vbt.MA.run(close, 10)
slow_ma = vbt.MA.run(close, 50)
entries = fast_ma.ma_crossed_above(slow_ma)
exits = fast_ma.ma_crossed_below(slow_ma)

pf_sma = vbt.Portfolio.from_signals(
    close,
    entries,
    exits,
    init_cash=100_000,
    freq='1D',
)
print(pf_sma.stats())

# ---------------------------------------------------------------------------
# 4. Post-process fees
# ---------------------------------------------------------------------------
print("\nAdjusting for fund redemption fees...")
adj = adjust_for_fund_fees(pf_sma.trades)
print(f"Original total return:  {pf_sma.total_return():.2%}")
print(f"Adjusted total return:  {adj['adj_return'].sum():.2%}")
print("\nTrade-level fee breakdown:")
print(adj[['hold_days', 'fee_rate', 'return', 'adj_return', 'pnl', 'adj_pnl']])

# ---------------------------------------------------------------------------
# 5. Plot (optional)
# ---------------------------------------------------------------------------
pf_sma.plot().show()
