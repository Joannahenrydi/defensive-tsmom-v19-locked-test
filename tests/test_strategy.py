import numpy as np
import pandas as pd

from strategy.v19 import SIGNAL_THRESHOLD, build_defensive_tsmom, frozen_trade_double_cost
from backtest.cross_asset import CrossAssetResult


def synthetic_data(periods=340, assets=("UP", "DOWN", "REVERSAL", "WEAK")):
    index = pd.bdate_range("2010-01-04", periods=periods)
    slopes = {"UP": .002, "DOWN": -.002, "REVERSAL": .002, "WEAK": .00005}
    close = pd.DataFrame(index=index, columns=assets, dtype=float)
    for name in assets:
        path = np.arange(periods) * slopes[name]
        if name == "REVERSAL":
            path[-40:] -= np.arange(40) * .008
        elif name == "WEAK":
            path = np.random.default_rng(6).normal(0, .01, periods).cumsum()
        close[name] = np.exp(path) * 100
    returns = close.pct_change(fill_method=None)
    eligibility = pd.DataFrame(True, index=index, columns=assets)
    return {"close": close, "returns": returns, "eligibility": eligibility}


def test_signal_is_directional_and_causal():
    data = synthetic_data()
    features = build_defensive_tsmom(data)
    last = features["signal"].iloc[-1]
    assert last.UP > SIGNAL_THRESHOLD
    assert last.DOWN < -SIGNAL_THRESHOLD
    assert last.REVERSAL == 0
    assert last.WEAK == 0
    cutoff = data["close"].index[-21]
    original = features["sizing_score"].loc[:cutoff]
    changed = {key: value.copy() for key, value in data.items()}
    changed["close"].loc[changed["close"].index > cutoff] *= 7
    changed["returns"] = changed["close"].pct_change(fill_method=None)
    revised = build_defensive_tsmom(changed)["sizing_score"].loc[:cutoff]
    pd.testing.assert_frame_equal(original, revised)


def test_double_cost_reprices_frozen_trades_only():
    index = pd.bdate_range("2022-01-03", periods=2)
    daily = pd.DataFrame({"gross_return": [.01, -.02], "transaction_cost": [.001, .002],
                          "borrow_cost": [.0001, .0002], "net_return": [.0089, -.0222]}, index=index)
    weights = pd.DataFrame({"A": [.5, .4]}, index=index)
    rebalances = pd.DataFrame({"turnover": [.2]}, index=index[:1])
    baseline = CrossAssetResult(daily, weights, rebalances, "COMPLETED", "OK")
    stressed = frozen_trade_double_cost(baseline)
    pd.testing.assert_frame_equal(stressed.weights, baseline.weights)
    pd.testing.assert_frame_equal(stressed.rebalances, baseline.rebalances)
    assert np.allclose(stressed.daily.transaction_cost, baseline.daily.transaction_cost * 2)
    assert np.allclose(stressed.daily.net_return,
                       baseline.daily.gross_return - stressed.daily.transaction_cost
                       - baseline.daily.borrow_cost)

