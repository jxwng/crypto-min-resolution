import json
import logging
import sys

import pandas as pd
import cvxportfolio as cp
from cmr.data_loader import load_ret
from cmr.returns import TaReturnsForecast
from cmr.risk import ReturnsCovRiskModel
from cmr.universe import build_universe
from cmr.strategy import CryptoStatArb

if __name__ == '__main__':
    # setup logger
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)

    # read config and create start/end time
    cfg = json.load(open(sys.argv[1]))
    print(cfg)
    start = pd.Timestamp(2020, 1, 1)
    end = pd.Timestamp(2022, 1, 30)

    # build universe
    symbols = build_universe(cfg['symbol_pattern'], start, end, cfg['adv_limit'], cfg['resample_rule'])

    # build predictions
    rf = TaReturnsForecast(symbols, start, end)
    train_result, test_result = rf.predict()
    signals = test_result['y_pred'].unstack(level='symbol')

    # build costs
    risk_model = ReturnsCovRiskModel(signals.columns[:-1], start, end).get_value()
    # tcost_model = cp.TcostModel(half_spread=cfg['half_spread'])  # transaction costs
    # bcost_model = cp.HcostModel(borrow_costs=borrow_costs / 250)  # borrow costs
    costs = [cfg['lambda_risk'] * cp.FullSigma(risk_model)]  # fit into cp format

    # build strategy
    optimizer = CryptoStatArb(signals, costs, **cfg['opt_kwargs'])

    # back-test
    returns = load_ret(signals.columns[:-1], start, end).fillna(0)
    market_sim = cp.MarketSimulator(returns, [], cash_key='cash')
    initial_portfolio = pd.Series(index=returns.columns, data=0)
    initial_portfolio.loc['cash'] = 1e5
    result = market_sim.run_backtest(initial_portfolio, signals.index[0], signals.index[-1], policy=optimizer)

    # performance analytics
    result.summary()
