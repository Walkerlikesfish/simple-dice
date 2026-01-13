import datetime
from simple_dice.backtest.backtest_feed import OpenFundCsvData, ETFCsvData
from simple_dice.strategy.simple_bt_strategy import TestStrategy, WeekStrategy

import backtrader as bt
import backtrader.analyzers as btanalyzers


if __name__ == '__main__':
    cerebro = bt.Cerebro()
    start_date = datetime.datetime(2024,12, 30)
    end_date = datetime.datetime(2026, 1, 9)

    data = OpenFundCsvData(dataname=r'../datas/161017.csv',
                           fromdate=start_date,
                           todate=end_date,)
    
    cerebro.adddata(data)
    cerebro.addstrategy(TestStrategy, volume_per_trade=4000) # WeekStrategy, TestStrategy
    
    # Add observers to plot buy/sell signals
    cerebro.addobserver(bt.observers.BuySell)
    cerebro.addobserver(bt.observers.Trades)
    

    init_cash = 10 * 10000.00
    cerebro.broker.setcash(init_cash)
    cerebro.broker.setcommission(commission=0.0)
    
    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    cerebro.run()

    # Print out the final result
    print(f'Init Cash: {init_cash}\nFinal Portfolio Value: {cerebro.broker.getvalue()}\nPortfolio cash: {cerebro.broker.get_cash()}\nTotal Profit: {cerebro.broker.getvalue() - init_cash}\nROI: {(cerebro.broker.getvalue() - init_cash)/init_cash * 100:.2f}%')

    # cerebro.addanalyzer(btanalyzers.SharpeRatio_A, _name='sharp')
    # cerebro.addanalyzer(btanalyzers.AnnualReturn, _name='annualreturn')

    # return_all = cerebro.broker.get_value() - cash
    # used_cash = cash - cerebro.broker.get_cash()
    # roi = round(return_all/used_cash, 2) * 100 if used_cash != 0 else 0
    # print('Sharpe Ratio:', strat.analyzers.sharp.get_analysis())
    # print('Annual Return:', strat.analyzers.annualreturn.get_analysis())
    # print(f"Used Cash: {used_cash}\nCurrent Cash: {cerebro.broker.get_cash()}\nReturn: {return_all}, ROI: {roi}%")

    cerebro.plot()