"""v19.1 cold-start one-month robustness episodes.

The underlying v19 signal, calibration, portfolio constraints and costs remain
unchanged.  Each episode starts from cash, uses historical data only for causal
state, trades at the starting-date close and measures the following 21 sessions.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest.cross_asset_budget import run_risk_budget_backtest
from portfolio.optimizer import estimate_costs
from strategy.v19 import (
    CONFIG,
    COSTS,
    FACTOR_CAPS,
    SLEEVE_CAPS,
    asset_sleeves,
    normalized_loadings,
)

HOLDING_SESSIONS = 21
WARMUP_SESSIONS = 130  # >=126 covariance window and divisible by 10-session rebalance interval.


def run_starting_point(
    decision_session: pd.Timestamp,
    score: pd.DataFrame,
    data: dict[str, pd.DataFrame],
    *,
    holding_sessions: int = HOLDING_SESSIONS,
) -> dict:
    """Run one causal cold-start episode and return its one-month diagnostics."""
    index = data["returns"].index
    if decision_session not in index:
        raise ValueError("decision session is not in the trading calendar")
    start_pos = int(index.get_loc(decision_session))
    end_pos = start_pos + holding_sessions
    if start_pos < WARMUP_SESSIONS or end_pos >= len(index):
        raise ValueError("insufficient warmup or forward sessions")
    window = index[start_pos - WARMUP_SESSIONS:end_pos + 1]
    eligibility = data["eligibility"].loc[window].copy()
    eligibility.loc[eligibility.index < decision_session] = False
    result = run_risk_budget_backtest(
        score.loc[window],
        data["returns"].loc[window],
        data["adv"].loc[window],
        eligibility & score.loc[window].notna(),
        normalized_loadings(),
        FACTOR_CAPS,
        asset_sleeves(),
        SLEEVE_CAPS,
        config=CONFIG,
        costs=COSTS,
    )
    if result.status != "COMPLETED":
        return {"decision_session": decision_session, "status": result.status,
                "reason": result.reason}
    realized_index = index[start_pos + 1:end_pos + 1]
    daily = result.daily.reindex(realized_index)
    if len(daily) != holding_sessions or daily.net_return.isna().any():
        raise RuntimeError("episode does not contain the prespecified realized sessions")
    nav = (1 + daily.net_return).cumprod()
    drawdown = nav / nav.cummax() - 1
    rebalances = result.rebalances.loc[decision_session:realized_index[-1]]
    if rebalances.empty or rebalances.index[0] != decision_session:
        raise RuntimeError("cold-start episode did not trade at the decision close")
    weights = result.weights.reindex(realized_index)
    last_session = realized_index[-1]
    last_weights = weights.iloc[-1]
    last_returns = data["returns"].loc[last_session].fillna(0)
    ending_weights = last_weights.mul(1 + last_returns).div(1 + daily.net_return.iloc[-1])
    history = data["returns"].loc[:last_session].tail(CONFIG.covariance_window)
    daily_volatility = history.std(ddof=1).reindex(ending_weights.index).fillna(0)
    liquidation = estimate_costs(
        ending_weights.to_numpy(),
        np.zeros(len(ending_weights)),
        daily_volatility.to_numpy(),
        data["adv"].loc[last_session].fillna(0).to_numpy(),
        CONFIG.nav,
        COSTS,
    )["transaction"]
    liquidated_nav = float(nav.iloc[-1] * (1 - liquidation))
    doubled_daily = daily.gross_return - 2 * daily.transaction_cost - daily.borrow_cost
    doubled_nav = float((1 + doubled_daily).prod() * (1 - 2 * liquidation))
    return {
        "decision_session": decision_session,
        "first_realized_session": realized_index[0],
        "last_realized_session": realized_index[-1],
        "status": "COMPLETED",
        "reason": "OK",
        "net_return": float(nav.iloc[-1] - 1),
        "liquidated_net_return": liquidated_nav - 1,
        "double_transaction_cost_liquidated_net_return": doubled_nav - 1,
        "gross_return": float((1 + daily.gross_return).prod() - 1),
        "max_drawdown": float(drawdown.min()),
        "positive_day_rate": float(daily.net_return.gt(0).mean()),
        "realized_volatility": float(daily.net_return.std(ddof=1) * np.sqrt(252)),
        "transaction_cost": float(daily.transaction_cost.sum()),
        "borrow_cost": float(daily.borrow_cost.sum()),
        "liquidation_transaction_cost": float(liquidation),
        "turnover": float(daily.turnover.sum()),
        "average_gross_exposure": float(daily.gross.mean()),
        "average_net_exposure": float(daily.net.mean()),
        "ending_long_exposure": float(weights.iloc[-1].clip(lower=0).sum()),
        "ending_short_exposure": float(weights.iloc[-1].clip(upper=0).abs().sum()),
        "rebalance_count": int(len(rebalances)),
        "numerical_boundary_solutions": int((~rebalances.optimizer_converged).sum()),
    }
