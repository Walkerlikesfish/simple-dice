# Design Discussion

## General Design
Basic functions:
- Trace current investment portfolio
    - Daily Update
    - Weekly, monthly report
- Selection and recommendation for investment portfolio
    - Back-testing supported estimation
- Database management
    - Daily update
    - Sanity check, quality check

Components:
- Use Denpendencies part defined existing projects to develop the feature. Do not develop from scratch.

### Dependencies
python==3.11

- Backtesting: https://vectorbt.dev/
- Portfolio optimization: https://github.com/PyPortfolio/PyPortfolioOpt
- Data source: https://akshare.akfamily.xyz 
