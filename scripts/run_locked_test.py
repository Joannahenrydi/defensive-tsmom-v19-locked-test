"""Run the frozen v19 2021-2024 locked test exactly once."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from backtest.engine import performance_metrics
from strategy.v19 import (
    DEVELOPMENT,
    FROZEN_CALIBRATION_DIGEST,
    FROZEN_CALIBRATION_SLOPE,
    FROZEN_SOURCE_SHA256,
    LOCKED_TEST,
    TRAIN,
    UNIVERSE,
    asset_sleeves,
    build_defensive_tsmom,
    calibration_audit,
    frozen_trade_double_cost,
    load_data,
    run_strategy,
    sha256,
)

PROTOCOL = Path("docs/V19_LOCKED_TEST_PROTOCOL.md")
FREEZE = Path("inputs/v19_development_freeze.json")
MAX_DRAWDOWN_GATE = -0.20


def segment_metrics(result, returns: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    daily = result.daily.loc[start:end]
    if result.status != "COMPLETED" or daily.empty:
        return {"status": result.status, "reason": result.reason}
    net = performance_metrics(daily.net_return)
    gross = performance_metrics(daily.gross_return)
    years = len(daily) / 252
    monthly = (1 + daily.net_return).groupby(daily.index.to_period("M")).prod() - 1
    yearly = (1 + daily.net_return).groupby(daily.index.year).prod() - 1
    market = returns["SPY"].reindex(daily.index)
    beta = float(daily.net_return.cov(market) / market.var())
    correlation = float(daily.net_return.corr(market))
    rebalances = result.rebalances.loc[start:end]
    net.update(
        status="COMPLETED",
        gross_sharpe=gross["sharpe"],
        gross_cagr=gross["cagr"],
        annual_turnover=float(daily.turnover.sum() / years),
        annual_transaction_cost=float(daily.transaction_cost.sum() / years),
        annual_borrow_cost=float(daily.borrow_cost.sum() / years),
        average_gross_exposure=float(daily.gross.mean()),
        average_net_exposure=float(daily.net.mean()),
        worst_month=float(monthly.min()),
        worst_calendar_year_return=float(yearly.min()),
        realized_spy_beta=beta,
        correlation_to_spy=correlation,
        rebalance_count=int(len(rebalances)),
        maximum_net_budget_ratio=float(rebalances.net_budget_ratio.max()),
        maximum_factor_budget_ratio=float(rebalances.maximum_factor_budget_ratio.max()),
        maximum_sleeve_budget_ratio=float(rebalances.maximum_sleeve_budget_ratio.max()),
        numerical_boundary_solutions=int((~rebalances.optimizer_converged).sum()),
    )
    return net


def top_drawdowns(net_returns: pd.Series, count: int = 5) -> pd.DataFrame:
    nav = (1 + net_returns).cumprod()
    peaks = nav.cummax()
    dd = nav / peaks - 1
    episodes: list[dict] = []
    in_episode = False
    start = peak_date = trough_date = None
    trough = 0.0
    for date, value in dd.items():
        if value < 0 and not in_episode:
            in_episode = True
            start = date
            prior = nav.loc[:date].iloc[:-1]
            peak_date = prior.idxmax() if not prior.empty else date
            trough_date, trough = date, float(value)
        elif value < 0 and in_episode and value < trough:
            trough_date, trough = date, float(value)
        elif value >= 0 and in_episode:
            episodes.append({"peak_date": peak_date, "start_date": start,
                             "trough_date": trough_date, "recovery_date": date,
                             "max_drawdown": trough,
                             "days_to_trough": int((trough_date - peak_date).days),
                             "days_to_recovery": int((date - peak_date).days)})
            in_episode = False
    if in_episode:
        episodes.append({"peak_date": peak_date, "start_date": start,
                         "trough_date": trough_date, "recovery_date": pd.NaT,
                         "max_drawdown": trough,
                         "days_to_trough": int((trough_date - peak_date).days),
                         "days_to_recovery": np.nan})
    return pd.DataFrame(episodes).sort_values("max_drawdown").head(count).reset_index(drop=True)


def attribution(result, data: dict, output: Path) -> dict:
    start, end = LOCKED_TEST
    returns = data["returns"].loc[start:end]
    weights = result.weights.reindex(index=returns.index, columns=returns.columns)
    contributions = weights * returns.fillna(0)
    daily = result.daily.loc[start:end]
    error = float(contributions.sum(axis=1).sub(daily.gross_return).abs().max())
    if not np.isfinite(error) or error > 1e-10:
        raise RuntimeError("asset contributions do not reconcile to gross return")

    yearly = []
    for year, index in daily.groupby(daily.index.year).groups.items():
        block = daily.loc[index]
        yearly.append({"year": int(year), "sessions": len(block),
                       "net_return": float((1 + block.net_return).prod() - 1),
                       "gross_return": float(block.gross_return.sum()),
                       "transaction_cost": float(block.transaction_cost.sum()),
                       "borrow_cost": float(block.borrow_cost.sum())})
    yearly_table = pd.DataFrame(yearly)
    yearly_table.to_csv(output / "yearly_attribution.csv", index=False)

    asset = contributions.sum().rename("gross_return_contribution").sort_values(ascending=False)
    asset_table = asset.rename_axis("symbol").reset_index()
    asset_table["absolute_contribution"] = asset_table.gross_return_contribution.abs()
    asset_table.to_csv(output / "asset_attribution.csv", index=False)

    sleeves = asset_sleeves()
    sleeve_table = asset.groupby(sleeves).sum().rename("gross_return_contribution").reset_index()
    sleeve_table = sleeve_table.sort_values("gross_return_contribution", ascending=False)
    sleeve_table.to_csv(output / "sleeve_attribution.csv", index=False)

    legs = pd.DataFrame({
        "leg": ["long", "short"],
        "gross_return_contribution": [
            float(contributions.where(weights.gt(0), 0).sum().sum()),
            float(contributions.where(weights.lt(0), 0).sum().sum()),
        ],
        "average_gross_exposure": [
            float(weights.clip(lower=0).sum(axis=1).mean()),
            float(weights.clip(upper=0).abs().sum(axis=1).mean()),
        ],
    })
    legs.to_csv(output / "long_short_attribution.csv", index=False)

    prior_close = data["close"]["SPY"].shift(1).loc[start:end]
    prior_peak = data["close"]["SPY"].cummax().shift(1).loc[start:end]
    drawdown = prior_close / prior_peak - 1
    regime = pd.Series(np.select([drawdown.lt(-.10), drawdown.le(-.05)],
                                 ["stress_below_10pct", "correction_5_to_10pct"],
                                 default="normal_above_5pct"), index=returns.index)
    regime_rows = []
    for name, index in regime.groupby(regime).groups.items():
        block = daily.loc[index]
        regime_rows.append({"regime": name, "sessions": len(block),
                            "net_return": float((1 + block.net_return).prod() - 1),
                            "gross_return_contribution": float(contributions.loc[index].sum().sum()),
                            "transaction_cost": float(block.transaction_cost.sum()),
                            "borrow_cost": float(block.borrow_cost.sum())})
    pd.DataFrame(regime_rows).to_csv(output / "drawdown_regime_attribution.csv", index=False)

    absolute = asset.abs().sort_values(ascending=False)
    top = absolute.head(5)
    concentration = {
        "top_5_absolute_contribution_share": float(top.sum() / absolute.sum()),
        "top_5_symbols": top.index.tolist(),
        "largest_contributor": str(asset.idxmax()),
        "largest_contribution": float(asset.max()),
        "largest_detractor": str(asset.idxmin()),
        "largest_detractor_contribution": float(asset.min()),
        "reconciliation_error": error,
    }
    (output / "contribution_concentration.json").write_text(json.dumps(concentration, indent=2) + "\n")
    top_drawdowns(daily.net_return).to_csv(output / "top_drawdowns.csv", index=False)
    return concentration


def main(source: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    source_hash = sha256(source)
    freeze = json.loads(FREEZE.read_text())
    source_ok = source_hash == FROZEN_SOURCE_SHA256 == freeze["source_sha256"]
    if not source_ok:
        raise RuntimeError("source snapshot does not match the v19 development freeze")

    data = load_data(source)
    features = build_defensive_tsmom(data)
    calibration = calibration_audit(features["sizing_score"], data["returns"])
    slope_ok = bool(np.isclose(calibration["slope"], FROZEN_CALIBRATION_SLOPE,
                               rtol=0, atol=1e-18))
    digest_ok = calibration["digest"] == FROZEN_CALIBRATION_DIGEST
    if not slope_ok or not digest_ok:
        raise RuntimeError("frozen train calibration failed to reproduce")

    score = features["sizing_score"] * FROZEN_CALIBRATION_SLOPE
    baseline = run_strategy(score, data)
    stressed = frozen_trade_double_cost(baseline)
    baseline.daily.to_csv(output / "baseline_daily.csv")
    baseline.rebalances.to_csv(output / "baseline_rebalances.csv")
    baseline.weights.to_csv(output / "baseline_weights.csv.gz", compression="gzip")
    stressed.daily.to_csv(output / "double_cost_daily.csv")

    baseline_metrics = segment_metrics(baseline, data["returns"], *LOCKED_TEST)
    stress_metrics = segment_metrics(stressed, data["returns"], *LOCKED_TEST)
    pd.DataFrame([
        {"evaluation": "baseline", **baseline_metrics},
        {"evaluation": "frozen_trade_double_transaction_cost", **stress_metrics},
    ]).to_csv(output / "evaluation.csv", index=False)
    concentration = attribution(baseline, data, output)

    risk_ok = all(baseline_metrics[key] <= 1.0001 for key in (
        "maximum_net_budget_ratio", "maximum_factor_budget_ratio", "maximum_sleeve_budget_ratio"
    ))
    data_end = data["returns"].index.max()
    integrity = {
        "source_sha256": source_hash,
        "source_matches_development_freeze": source_ok,
        "protocol_sha256": sha256(PROTOCOL),
        "frozen_inputs_sha256": sha256(FREEZE),
        "train_calibration": calibration,
        "calibration_slope_reproduced": slope_ok,
        "calibration_digest_reproduced": digest_ok,
        "universe_count": len(data["returns"].columns),
        "universe_exact": list(data["returns"].columns) == UNIVERSE,
        "data_start": str(data["returns"].index.min().date()),
        "data_end": str(data_end.date()),
        "locked_test_start": str(LOCKED_TEST[0].date()),
        "locked_test_end": str(LOCKED_TEST[1].date()),
        "locked_test_sessions": int(len(data["returns"].loc[LOCKED_TEST[0]:LOCKED_TEST[1]])),
        "risk_budgets_satisfied": risk_ok,
        "attribution_reconciliation_error": concentration["reconciliation_error"],
    }
    integrity_passed = bool(
        source_ok and slope_ok and digest_ok and integrity["universe_exact"]
        and data_end == LOCKED_TEST[1] and risk_ok
        and concentration["reconciliation_error"] <= 1e-10
        and baseline.status == "COMPLETED"
    )
    integrity["passed"] = integrity_passed
    (output / "integrity_audit.json").write_text(json.dumps(integrity, indent=2) + "\n")

    gates = {
        "integrity_and_execution": integrity_passed,
        "net_cagr_positive": baseline_metrics.get("cagr", -np.inf) > 0,
        "net_sharpe_positive": baseline_metrics.get("sharpe", -np.inf) > 0,
        "max_drawdown_no_worse_than_minus_20pct":
            baseline_metrics.get("max_drawdown", -np.inf) >= MAX_DRAWDOWN_GATE,
        "double_transaction_cost_cagr_positive": stress_metrics.get("cagr", -np.inf) > 0,
        "double_transaction_cost_sharpe_positive": stress_metrics.get("sharpe", -np.inf) > 0,
    }
    passed = bool(all(gates.values()))
    decision = {
        "status": "V19_LOCKED_TEST_PASSED" if passed else "V19_LOCKED_TEST_FAILED",
        "locked_test_evaluated": True,
        "locked_test_read_count": 1,
        "orders_allowed": False,
        "gates": gates,
        "baseline_metrics": baseline_metrics,
        "double_transaction_cost_metrics": stress_metrics,
        "diagnostics_are_nonselective": True,
        "no_refit_permitted": True,
    }
    (output / "decision.json").write_text(json.dumps(decision, indent=2) + "\n")
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("inputs/etf_daily.csv"))
    parser.add_argument("--output", type=Path, default=Path("reports/locked_test"))
    arguments = parser.parse_args()
    main(arguments.source, arguments.output)

