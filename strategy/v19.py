"""Frozen v19 defensive time-series momentum definition.

This module contains the one strategy evaluated in this repository.  It has no
candidate grid and performs no parameter selection on the locked test.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from backtest.cross_asset import CrossAssetResult
from backtest.cross_asset_budget import RiskBudgetConfig, run_risk_budget_backtest
from portfolio.optimizer import PortfolioCosts

TRAIN = (pd.Timestamp("2008-01-02"), pd.Timestamp("2016-12-30"))
DEVELOPMENT = (pd.Timestamp("2017-01-03"), pd.Timestamp("2020-12-31"))
LOCKED_TEST = (pd.Timestamp("2021-01-04"), pd.Timestamp("2024-12-31"))

UNIVERSE = [
    "SPY", "QQQ", "IWM", "XLC", "XLY", "XLP", "XLE", "XLF", "XLV", "XLI",
    "XLB", "XLK", "XLU", "EFA", "EEM", "EWJ", "EWU", "EWZ", "FXI", "INDA",
    "VNQ", "BIL", "SHY", "IEF", "TLT", "TIP", "GOVT", "LQD", "HYG", "EMB",
    "MUB", "GLD", "SLV", "DBC", "PDBC", "USO", "UNG", "DBA", "CPER", "CORN",
    "WEAT", "UUP", "FXE", "FXY", "FXB",
]

MOMENTUM_WEIGHTS = {63: 0.25, 126: 0.35, 252: 0.40}
SKIP_SESSIONS = 21
VOLATILITY_WINDOW = 60
MOVING_AVERAGE_WINDOW = 200
SIGNAL_THRESHOLD = 0.25
FROZEN_CALIBRATION_SLOPE = 6.537825607487585e-06
FROZEN_CALIBRATION_DIGEST = "d59984125ff01d469e8b75ded4e674f6a8708b1f066b92d9ce8ef5a744ab9122"
FROZEN_SOURCE_SHA256 = "82347fef112a5f04dc2b5accf947f362eefe1a0a89f1c59bf143a369ab63e32e"

FACTOR_CAPS = pd.Series(
    {"equity": 0.50, "duration": 0.50, "credit": 0.30, "commodity": 0.50, "usd": 0.40}
)
SLEEVE_CAPS = pd.Series(
    {"equity": 0.60, "rates": 0.60, "credit": 0.40, "metals": 0.40,
     "commodity": 0.60, "usd": 0.30}
)
CONFIG = RiskBudgetConfig(
    rebalance_every=10,
    covariance_window=126,
    covariance_shrinkage=0.50,
    max_gross=1.0,
    max_name=0.10,
    max_turnover=0.25,
    max_participation=0.001,
    annual_volatility_cap=0.08,
    net_cap=0.60,
    nav=100_000.0,
    tolerance=1e-7,
    max_iterations=500,
)
COSTS = PortfolioCosts(
    commission_bps=0,
    half_spread_bps=1,
    slippage_bps=1,
    impact_coefficient=0.10,
    borrow_annual=0.01,
    calendar_days=7,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_data(path: Path, end: pd.Timestamp = LOCKED_TEST[1]) -> dict[str, pd.DataFrame]:
    raw = pd.read_csv(path, parse_dates=["date"])
    raw = raw.loc[raw.date.le(end) & raw.symbol.isin(UNIVERSE)].copy()
    dates = pd.DatetimeIndex(sorted(raw.loc[raw.symbol.eq("SPY"), "date"].unique()))

    def pivot(field: str) -> pd.DataFrame:
        return raw.pivot(index="date", columns="symbol", values=field).reindex(
            index=dates, columns=UNIVERSE
        )

    close = pivot("adj_close")
    volume = pivot("volume")
    returns = close.pct_change(fill_method=None)
    adv = (pivot("close") * volume).rolling(60, min_periods=60).median().shift(1)
    history = returns.notna().rolling(252, min_periods=1).sum().shift(1)
    eligibility = returns.notna() & close.notna() & volume.gt(0) & adv.gt(0) & history.ge(252)
    return {"close": close, "volume": volume, "returns": returns, "adv": adv,
            "eligibility": eligibility}


def factor_loadings() -> pd.DataFrame:
    frame = pd.DataFrame(
        0.0, index=UNIVERSE, columns=["equity", "duration", "credit", "commodity", "usd"]
    )
    frame.loc[["SPY", "QQQ", "IWM"], "equity"] = [1.0, 1.1, 1.1]
    sectors = ["XLC", "XLY", "XLP", "XLE", "XLF", "XLV", "XLI", "XLB", "XLK", "XLU"]
    frame.loc[sectors, "equity"] = 1.0
    frame.loc[["EFA", "EEM", "EWJ", "EWU", "EWZ", "FXI", "INDA"], "equity"] = [
        .9, 1.0, .8, .8, 1.1, 1.0, 1.0,
    ]
    frame.loc[["VNQ", "LQD", "HYG", "EMB"], "equity"] = [.7, .1, .4, .2]
    frame.loc[["BIL", "SHY", "IEF", "TLT", "TIP", "GOVT", "LQD", "HYG", "EMB", "MUB"],
              "duration"] = [.1, 1, 4, 15, 7, 6, 8, 3, 7, 6]
    frame.loc[["LQD", "HYG", "EMB", "MUB"], "credit"] = [.4, 1.0, .8, .2]
    commodities = ["GLD", "SLV", "DBC", "PDBC", "USO", "UNG", "DBA", "CPER", "CORN", "WEAT"]
    frame.loc[commodities, "commodity"] = [.3, .5, 1, 1, 1.2, 1.5, .8, 1, 1, 1]
    frame.loc["UUP", "usd"] = 1.0
    frame.loc[["FXE", "FXY", "FXB"], "usd"] = -1.0
    frame.loc[["EFA", "EEM", "EWJ", "EWU", "EWZ", "FXI", "INDA"], "usd"] = -.3
    frame.loc[commodities, "usd"] = -.3
    return frame


def asset_sleeves() -> pd.Series:
    mapping: dict[str, str] = {}
    equity = {"SPY", "QQQ", "IWM", "XLC", "XLY", "XLP", "XLE", "XLF", "XLV", "XLI",
              "XLB", "XLK", "XLU", "EFA", "EEM", "EWJ", "EWU", "EWZ", "FXI", "INDA", "VNQ"}
    rates = {"BIL", "SHY", "IEF", "TLT", "TIP", "GOVT"}
    credit = {"LQD", "HYG", "EMB", "MUB"}
    metals = {"GLD", "SLV"}
    commodity = {"DBC", "PDBC", "USO", "UNG", "DBA", "CPER", "CORN", "WEAT"}
    for symbol in UNIVERSE:
        mapping[symbol] = (
            "equity" if symbol in equity else "rates" if symbol in rates else
            "credit" if symbol in credit else "metals" if symbol in metals else
            "commodity" if symbol in commodity else "usd"
        )
    return pd.Series(mapping, name="sleeve").reindex(UNIVERSE)


def normalized_loadings() -> pd.DataFrame:
    frame = factor_loadings()
    return frame.div(frame.abs().max().replace(0, 1), axis=1)


def build_defensive_tsmom(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    close, returns, eligibility = data["close"], data["returns"], data["eligibility"]
    log_price = np.log(close)
    daily_volatility = returns.rolling(VOLATILITY_WINDOW, min_periods=VOLATILITY_WINDOW).std().shift(1)
    components = {}
    for horizon, weight in MOMENTUM_WEIGHTS.items():
        move = log_price.shift(SKIP_SESSIONS).sub(log_price.shift(horizon))
        components[horizon] = move.div(daily_volatility * np.sqrt(horizon - SKIP_SESSIONS)) * weight
    raw_signal = sum(components.values()).clip(-3, 3)
    moving_average = close.rolling(MOVING_AVERAGE_WINDOW, min_periods=MOVING_AVERAGE_WINDOW).mean()
    confirmed = ((raw_signal.gt(0) & close.gt(moving_average)) |
                 (raw_signal.lt(0) & close.lt(moving_average)))
    signal = raw_signal.where(confirmed, 0.0)
    signal = signal.where(signal.abs().ge(SIGNAL_THRESHOLD), 0.0).where(eligibility)
    annualized_volatility = daily_volatility * np.sqrt(252)
    sizing_score = signal.div(annualized_volatility.where(annualized_volatility.gt(0)))
    return {"raw_signal": raw_signal.where(eligibility),
            "moving_average": moving_average.where(eligibility),
            "signal": signal,
            "annualized_volatility": annualized_volatility.where(eligibility),
            "sizing_score": sizing_score.where(eligibility)}


def forward_total_return_labels(returns: pd.DataFrame, horizon: int = 5):
    labels = pd.DataFrame(1.0, index=returns.index, columns=returns.columns)
    for step in range(1, horizon + 1):
        labels *= 1 + returns.shift(-step)
    end = pd.Series(returns.index, index=returns.index).shift(-horizon)
    return labels - 1, end


def calibration_audit(score: pd.DataFrame, returns: pd.DataFrame) -> dict:
    labels, label_end = forward_total_return_labels(returns, 5)
    completed = label_end.le(TRAIN[1])
    train_score = score.loc[TRAIN[0]:TRAIN[1]].where(completed.loc[TRAIN[0]:TRAIN[1]])
    train_label = labels.loc[TRAIN[0]:TRAIN[1]].where(completed.loc[TRAIN[0]:TRAIN[1]])
    x, y = train_score.to_numpy().ravel(), train_label.to_numpy().ravel()
    usable = np.isfinite(x) & np.isfinite(y)
    slope = float(x[usable] @ y[usable] / (x[usable] @ x[usable] + 1e-6))
    digest = hashlib.sha256(np.c_[x[usable], y[usable]].tobytes()).hexdigest()
    return {"slope": slope, "digest": digest, "observations": int(usable.sum())}


def run_strategy(score: pd.DataFrame, data: dict[str, pd.DataFrame]) -> CrossAssetResult:
    return run_risk_budget_backtest(
        score, data["returns"], data["adv"], data["eligibility"] & score.notna(),
        normalized_loadings(), FACTOR_CAPS, asset_sleeves(), SLEEVE_CAPS,
        config=CONFIG, costs=COSTS,
    )


def frozen_trade_double_cost(baseline: CrossAssetResult) -> CrossAssetResult:
    daily = baseline.daily.copy()
    daily["transaction_cost"] *= 2.0
    daily["net_return"] = daily["gross_return"] - daily["transaction_cost"] - daily["borrow_cost"]
    return CrossAssetResult(daily, baseline.weights.copy(), baseline.rebalances.copy(),
                            baseline.status, baseline.reason)

