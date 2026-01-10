import datetime
from simple_dice.backtest.backtest_feed import OpenFundCsvData, ETFCsvData
from simple_dice.strategy.simple_bt_strategy import DeclineStrategy

import backtrader as bt
import backtrader.analyzers as btanalyzers


if __name__ == '__main__':
    cerebro = bt.Cerebro()
    start_date = datetime.datetime(2025, 10, 2)
    end_date = datetime.datetime(2026, 1, 2)

    data = OpenFundCsvData(dataname=r'../datas/161017.csv',
                           fromdate=start_date,
                           todate=end_date,)

    # data1 = ETFCsvData(dataname=r'datas/sh510500.csv', fromdate=start_date, todate=end_date)
    
    cerebro.adddata(data)
    cerebro.addstrategy(DeclineStrategy)

    cash = 10000.00
    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=0.00015)

    cerebro.addanalyzer(btanalyzers.SharpeRatio_A, _name='sharp')
    cerebro.addanalyzer(btanalyzers.AnnualReturn, _name='annualreturn')

    strats = cerebro.run()
    strat = strats[0]

    return_all = cerebro.broker.get_value() - cash
    used_cash = cash - cerebro.broker.get_cash()
    
    roi = round(return_all/used_cash, 2) * 100 if used_cash != 0 else 0
    print('Sharpe Ratio:', strat.analyzers.sharp.get_analysis())
    print('Annual Return:', strat.analyzers.annualreturn.get_analysis())
    print(f'Total Gain: {roi}%')

    cerebro.plot()