import calendar
import backtrader as bt


class MomOscStrategy(MyStrategy):
    params = (
        ('period', 20),
        ('printlog', True),
    )

    def __init__(self):
        self.dataprice = self.datas[0].close
        self.order = None
        self.month = -1
        self.mom = [
            bt.indicators.MomentumOscillator(i, period=self.params.period)
            for i in self.datas
        ]

    def next(self):
        buy_id = 999

        c = [i.momosc[0] for i in self.mom]
        [self.log(f'{self.datas[c.index(i)]._name}, {i}') for i in c]

        value, value1, value2 = map(lambda x: x, c)
        index, value = c.index(max(c)), max(c)

        if value > 100:
            buy_id = index

        if value > 100 and value1 > 100 and value2 > 100:
            buy_id = 888

        for i in range(0, len(c)):

            if buy_id != 888 and i != buy_id:
                position_size = self.broker.getposition(
                    data=self.datas[i]).size
                if position_size != 0:
                    self.order_target_percent(data=self.datas[i], target=0)

        if buy_id != 999 and buy_id != 888:
            position_size = self.broker.getposition(
                data=self.datas[buy_id]).size
            if position_size == 0:
                self.order_target_percent(data=self.datas[buy_id], target=0.98)

    def stop(self):
        return_all = self.broker.getvalue() / 200000.0
        print('{0}, {1}%, {2}%'.format(
            self.params.period, round((return_all - 1.0) * 100, 2),
            round((pow(return_all, 1.0 / 8) - 1.0) * 100, 2)))


class MomStrategy(MyStrategy):
    params = (
        ('period', 20),
        ('printlog', True),
    )

    def __init__(self):
        self.dataprice = self.datas[0].close
        self.order = None
        self.month = -1
        self.mom = [
            bt.indicators.Momentum(i, period=self.params.period)
            for i in self.datas
        ]

    def next(self):
        buy_id = 999

        c = [
            i.momentum[0]  #/ (i.datas[0].close + i.datas[0].open) * 2
            for i in self.mom
        ]
        index, value = c.index(max(c)), max(c)
        [self.log(f'{self.datas[c.index(i)]._name}, {i}') for i in c]
        if value > 0:
            buy_id = index

        for i in range(0, len(c)):
            if i != buy_id:
                position_size = self.broker.getposition(
                    data=self.datas[i]).size
                if position_size != 0:
                    self.order_target_percent(data=self.datas[i], target=0)

        if buy_id != 999:
            position_size = self.broker.getposition(
                data=self.datas[buy_id]).size
            if position_size == 0:
                self.order_target_percent(data=self.datas[buy_id], target=0.98)

    def stop(self):
        return_all = self.broker.getvalue() / 200000.0
        print('{0}, {1}%, {2}%'.format(
            self.params.period, round((return_all - 1.0) * 100, 2),
            round((pow(return_all, 1.0 / 8) - 1.0) * 100, 2)))


class BBandStrategy(bt.Strategy):
    params = (('period', 20), )

    def __init__(self):
        self.dataprice = self.datas[0].close
        self.order = None
        self.month = -1
        self.bbandPcts = [
            bt.indicators.BollingerBandsPct(i, period=self.params.period)
            for i in self.datas
        ]

    def next(self):
        buy_id = 0

        c = [i.pctb[0] for i in self.bbandPcts]
        index, value = c.index(max(c)), max(c)

        if value > 0:
            buy_id = index

        for i in range(0, len(c)):
            if i != buy_id:
                position_size = self.broker.getposition(
                    data=self.datas[i]).size
                if position_size != 0:
                    self.order_target_percent(data=self.datas[i], target=0)

        position_size = self.broker.getposition(data=self.datas[buy_id]).size
        if position_size == 0:
            self.order_target_percent(data=self.datas[buy_id], target=0.98)

    def stop(self):
        return_all = self.broker.getvalue() / 200000.0
        print('{0}, {1}%, {2}%'.format(
            self.params.period, round((return_all - 1.0) * 100, 2),
            round((pow(return_all, 1.0 / 8) - 1.0) * 100, 2)))


class BBandMomoscStrategy(MyStrategy):
    """
    先找到动量最好的一支，然后判断，如果跌破布林下线则买入，跌破中线买入一半，从中线上涨到上线则卖出二分之一，从下线上涨到布林中线卖出二分之一。
    """

    params = (
        ('period', 20),
        ('printlog', True),
    )

    def __init__(self):
        self.dataprice = [i.close for i in self.datas]
        self.order = None
        self.mom = [
            bt.indicators.MomentumOscillator(i, period=self.params.period)
            for i in self.datas
        ]

        self.bbandPcts = [
            bt.indicators.BollingerBandsPct(i, period=self.params.period)
            for i in self.datas
        ]

    def next(self):
        buy_id = 0

        momosc = [i.momosc[0] for i in self.mom]
        top = [i.top[0] for i in self.bbandPcts]
        mid = [i.mid[0] for i in self.bbandPcts]
        bot = [i.bot[0] for i in self.bbandPcts]
        pctb = [i.pctb[0] for i in self.bbandPcts]
        index, value = momosc.index(max(momosc)), max(momosc)

        if value > 100:
            buy_id = index

        for i in range(0, len(momosc)):
            if i != buy_id:
                position_size = self.broker.getposition(
                    data=self.datas[i]).size
                if position_size != 0:
                    self.order_target_percent(data=self.datas[i], target=0)

        position_size = self.broker.getposition(data=self.datas[buy_id]).size
        if position_size == 0 and self.dataprice[buy_id] < bot[buy_id]:
            self.order_target_percent(data=self.datas[buy_id], target=0.98)

    def stop(self):
        return_all = self.broker.getvalue() / 200000.0
        print('{0}, {1}%, {2}%'.format(
            self.params.period, round((return_all - 1.0) * 100, 2),
            round((pow(return_all, 1.0 / 8) - 1.0) * 100, 2)))