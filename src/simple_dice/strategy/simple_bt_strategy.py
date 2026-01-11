import calendar
import datetime
import os.path
import time
import backtrader as bt


# A test strategy
class TestStrategy(bt.Strategy):
    params = (('volume_per_trade', 2500), )

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders
        self.order = None
        self.buy_date = None
        self.buy_queue = []
        self.sma = bt.indicators.SMA(self.dataclose, period=7)

    def calculate_sell_commission(self, sell_price):
        dt = self.datas[0].datetime.date(0)
        commission = 0
        for buy_date, buy_size, _ in self.buy_queue:
            days = (dt - buy_date).days
            if days < 7:
                comm_rate = 0.015
            elif days < 30:
                comm_rate = 0.005
            else:
                comm_rate = 0.0
            commission += buy_size * sell_price * comm_rate
        return commission

    def notify_order(self, order):
        dt = self.datas[0].datetime.date(0)
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.buy_date = dt
                self.buy_queue.append((dt, order.executed.size, order.executed.price))
            else:  # Sell
                commission = 0
                sold_size = order.executed.size
                price = order.executed.price
                while sold_size > 0 and self.buy_queue:
                    buy_date, buy_size, _ = self.buy_queue[0]
                    sell_portion = min(buy_size, sold_size)
                    days = (dt - buy_date).days
                    if days < 7:
                        comm_rate = 0.015
                    elif days < 30:
                        comm_rate = 0.005
                    else:
                        comm_rate = 0.0
                    commission += sell_portion * price * comm_rate
                    if sell_portion >= buy_size:
                        self.buy_queue.pop(0)
                    else:
                        self.buy_queue[0] = (buy_date, buy_size - sell_portion, self.buy_queue[0][2])
                    sold_size -= sell_portion
                self.broker.add_cash(-commission)
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          commission))

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))
    

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log(f'Close: {self.dataclose[0]:.2f}, Current position size: {self.position.size}')

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Buy policy: when signal shows, buy for 6 days (signal + 5 more)
        if len(self) > 7:
            decline = (self.sma[0] - self.sma[-7]) / self.sma[-7]
            if decline < -0.005 and not hasattr(self, 'buy_counter'):
                self.buy_counter = 6
                self.buy_start_ma = self.sma[0]
            if hasattr(self, 'buy_counter') and self.buy_counter > 0 and self.sma[0] <= self.buy_start_ma * 1.005:
                buy_size = round(self.params.volume_per_trade / self.dataclose[0], 2)
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                self.order = self.buy(size=buy_size)
                self.buy_counter -= 1
                if self.buy_counter == 0:
                    delattr(self, 'buy_counter')
                    delattr(self, 'buy_start_ma')

        # Sell policy: if >0.8% net gain after commission, sell all
        if self.position.size > 0:
            sell_value = self.dataclose[0] * self.position.size
            commission = self.calculate_sell_commission(self.dataclose[0])
            total_cost = sum(buy_size * buy_price for _, buy_size, buy_price in self.buy_queue)
            if total_cost > 0:
                net_gain = sell_value - commission - total_cost
                if net_gain / total_cost > 0.008:
                    self.log(f'SELL ALL CREATE due to >0.8% net gain, {self.dataclose[0]}')
                    self.order = self.sell(size=self.position.size)
                    # return  # sell all, skip other policies

        # # Sell policy: when signal shows, sell for 6 days
        # if self.position and len(self) > 7:
        #     increase = (self.sma[0] - self.sma[-7]) / self.sma[-7]
        #     if increase > 0.01 and not hasattr(self, 'sell_counter'):
        #         self.sell_counter = 6
        #     if hasattr(self, 'sell_counter') and self.sell_counter > 0:
        #         sell_size = self.position.size / self.sell_counter
        #         self.log('SELL CREATE, %.2f' % self.dataclose[0])
        #         self.order = self.sell(size=sell_size)
        #         self.sell_counter -= 1
        #         if self.sell_counter == 0:
        #             delattr(self, 'sell_counter')


class WeekStrategy(bt.Strategy):
    params = (('weeknum', 3), ('volume_per_trade', 2500), )

    def weekday(self, date):
        date_time = date
        return (calendar.weekday(date_time.year, date_time.month,
                                 date_time.day))

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        self.dataprice = self.datas[0].close
        self.dataclose = self.datas[0].close

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None
    
    def next(self):
        if self.weekday(self.datas[0].datetime.date(0)) == self.params.weeknum:
            buy_size = round(self.params.volume_per_trade / self.dataprice[0], 2)
            self.log('BUY CREATE, %.2f' % self.dataclose[0])
            self.buy(size=buy_size)
