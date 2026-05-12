# Plan: simple-dice rebuild on vectorbt + PyPortfolioOpt + AKShare

Reference: [`agent_read/design_discussion.md`](agent_read/design_discussion.md)

## Goals
1. Portfolio tracking — daily MTM + weekly/monthly report.
2. Portfolio selection/recommendation — backtest-validated allocations.
3. Database management — daily AKShare sync + sanity checks.

Constraint: reuse vectorbt, PyPortfolioOpt, AKShare; do not re-implement.

## Stack
- Python 3.11 (conda env `py311`)
- Data: AKShare; Backtest: vectorbt; Optimization: PyPortfolioOpt
- Holdings: YAML; Report: Markdown + Plotly Dash; Scheduler: manual cron

## Locked design decisions
- **Storage**: YAML for holdings and recommendations.
- **Universe**: cross-category.
- **Cadence**: on-demand + manual weekly run (Friday EOD).
- **Reports**: both Markdown file and Plotly Dash app.
- **Fee fidelity**: lot-by-lot, FIFO first with pluggable matcher interface.
- **Benchmarks**: CSI 300 (`sh000300`) **and** AUM-weighted category average.
- **Legacy code**: delete after migration.

## Universe filter (defaults)
1. History ≥ 504 trading days.
2. Completeness ≥ 95% of expected days.
3. Exclude `暂停申购` / `暂停赎回`.
4. Fund age ≥ 1 year.
5. AUM ≥ 100M CNY.
6. Share-class dedup ON by default; keep lowest-fee class per family.
7. Index-tracking dedup ON; keep highest-AUM fund per tracked index, **report which were deduped**.
8. Category must have ≥ 10 funds.
9. QDII included by default; user disables via category upper bound = 0.

## Category caps (defaults, user-adjustable)
| Category | Upper |
|---|---|
| 股票型 | 60% |
| 混合型 | 50% |
| 债券型 | 40% |
| QDII | 20% |
| 货币型 | 30% |
| single fund | 20% |

Applied via `pypfopt.EfficientFrontier.add_sector_constraints`.

## Phases

### Phase 1 — Database layer
- `simple_dice.data.repository.FundRepository(cache_dir)` with `init() / update() / check()`.
- Move legacy `data_openfund_get.py` logic into the module.
- `simple_dice.data.quality` sanity checks: missing days, NaN, sigma jumps, staleness.
- Benchmark ingestion:
  - CSI 300 via `ak.stock_zh_index_daily_em(symbol='sh000300')` → `frame_index/`.
  - AUM per fund via `ak.fund_open_fund_rank_em()` (primary), per-fund `fund_open_fund_info_em(..., '规模')` (backup) → `meta/aum.csv`.
  - AUM-weighted category averages → `frame_cat_avg/`.
- CLI: `python -m simple_dice.data {init,update,check}`.

### Phase 2 — Backtest framework
- `simple_dice.backtest.runner` — opinionated vbt.Portfolio wrapper (freq=1D, project defaults).
- `simple_dice.strategy.signals`:
  - Buy-and-hold, SMA/EMA crossover, momentum oscillator (vbt indicator factory), windowed-quantile.
- Parameter sweep helpers (vbt `run_combs`, heatmap).

### Phase 3 — Portfolio optimization (recommendation)
- `simple_dice.portfolio.universe.select_universe(repository, **filter_kwargs)`.
- `simple_dice.portfolio.optimize`:
  - `expected_returns(data, method='mean_historical')`
  - `risk_model(data, method='ledoit_wolf')`
  - `recommend(universe, objectives=['max_sharpe'], category_caps=DEFAULTS, single_fund_cap=0.2)`
  - Returns weight dicts keyed by objective name.
- Validation: backtest each weight set with vbt against CSI 300 + category-average benchmarks.
- Writer: `recommendation_YYYY-MM-DD.yaml` in `<cache_dir>/recommendations/`, **single file** with sections per objective and a `deduped_funds` block listing index-tracking duplicates that were dropped.

### Phase 4 — Holdings tracker
- YAML schema:
  ```yaml
  holdings:
    - code: '161017'
      lots:
        - lot_id: '161017-2024-06-01-1'
          buy_date: 2024-06-01
          buy_price: 2.30
          shares: 1000
      sells:
        - sell_date: 2024-09-01
          sell_price: 2.50
          shares: 300
          matched_lots:
            - lot_id: '161017-2024-06-01-1'
              shares: 300
              hold_days: 92
              fee_rate: 0.0
  ```
- `simple_dice.holdings.lots`:
  - `Lot`, `Position` dataclasses.
  - `LotMatcher` protocol with `FIFOMatcher` impl; stub `SpecificLotMatcher`.
- `simple_dice.holdings.fees` — tiered redemption fee per lot (< 7 d: 1.5%, 7–30 d: 0.5%, > 30 d: 0%).
- `simple_dice.holdings.tracker`:
  - `mark_to_market(holdings, repository, as_of)` → current value, unrealised P&L.
  - `realised_returns(holdings)` → from `sells` history.
- `simple_dice.holdings.report`:
  - Shared data prep → markdown writer + Plotly Dash app.
  - Per-fund return contribution, fee impact, benchmark comparison (CSI 300 + cat-avg).
- CLI:
  - `python -m simple_dice.holdings status`
  - `python -m simple_dice.holdings report --period {weekly,monthly} --out report.md`
  - `python -m simple_dice.holdings dashboard` (Dash on localhost:8050)
  - `python -m simple_dice.holdings recommend` (writes proposal YAML, **always full weights**)

### Phase 5 — Cleanup
- Delete:
  - `src/simple_dice/backtest/{backtest_feed,bt_cerebro_mod}.py`
  - `src/simple_dice/strategy/{simple_bt_strategy,momoent_osci_strategy}.py`
  - `scripts/v0/run_open_fund_bt.py`
- `pyproject.toml`: drop `backtrader`, `backtrader_plotting`; add `vectorbt`, `pyportfolioopt`, `pyyaml`, `plotly`, `dash`, `jinja2`.
- Lightweight tests under `tests/`:
  - data layer (cache + filter)
  - FIFO lot matcher correctness
  - fee tier boundaries (6/7/29/30/31 days)
- Update `AGENTS.md` to reflect new module map.

## First slice (week-1 deliverable)
Smallest end-to-end path proving the pipeline:
1. Phase 1 minimal: `FundRepository.update()` + sanity check + CSI 300 + AUM.
2. Phase 3 minimal: universe filter + `recommend(['max_sharpe'])` with default caps.
3. Phase 4 minimal: write `recommendation_YYYY-MM-DD.yaml` (proposal only).
4. Backtest the recommendation vs both benchmarks.
5. One CLI: `python -m simple_dice recommend --top 20`.

## Open items deferred
- Black-Litterman or factor-based expected returns (v2).
- Specific-lot identification matcher (interface stub only in v1).
- Auto-execution / broker integration (out of scope).
- Stock / futures / options support (fund-only for now).

## Operational notes
- Weekly proposal YAML includes both **target weights** and a **diff vs current holdings** section, so review is fast even though we always show full target weights.
- Dash app is **read-only** (display current MTM, P&L, weekly history). No order entry.
- `pyproject.toml` becomes the single source of dependency truth; `requirements.txt` removed in Phase 5.
