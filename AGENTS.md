# simple-dice

Backtrader-based open fund backtesting (migrating to vectorbt). Author: Yu Liu / Walker.

## Quick start

```bash
pip install -e .         # installs `simple_dice` package from src/
```

## Design direction (`doc/agent_read/design_discussion.md`)

- Python 3.11
- Backtesting: **vectorbt** (replacing backtrader)
- Portfolio optimization: **PyPortfolioOpt**

## Package layout

```
src/simple_dice/         # library code
  backtest/              # backtrader feed parsers & cerebro runners
  data/                  # data processing (windowed revenue calc)
  strategy/              # backtrader strategy classes
  vis/                   # matplotlib visualization helpers
scripts/v0/              # actual entrypoints (not part of library)
```

The `src/` layout uses `package_dir={"": "src"}` in `setup.py` — imports are `from simple_dice.backtest.backtest_feed import ...`.

## Known issues

- `src/simple_dice/backtest/bt_cerebro_mod.py:9` imports `from backtest.backtest_feeds import ETFCsvData` — wrong path (should be `simple_dice.backtest.backtest_feed`). Likely stale.
- `src/simple_dice/strategy/momoent_osci_strategy.py` references undefined `MyStrategy` base class. Likely stale.
- No CI, no tests, no linter/formatter config — only checked by Python runtime.

## Data

Scripts in `scripts/v0/` hardcode a local data directory: `/Users/yuliu/Documents/workspace/data/dice_data/open_fund/`. This is not portable. CSV data in `datas/` is gitignored.

## Commit style

Uses conventional commits with bracket prefixes: `[feat]`, `[add]`, `[clean]`, `[fix]`.
