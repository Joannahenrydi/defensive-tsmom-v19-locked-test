# v19.1 Daily Starting-Point Robustness Experiment

v19.1 is a cold-start robustness experiment around the frozen v19 strategy. It does not alter the
universe, alpha signal, calibration, optimizer, risk limits, execution convention or costs. Its
executable wrapper is [`strategy/v19_1.py`](strategy/v19_1.py), and it calls the same portfolio
engine used by v19.

## Experiment definition

Every eligible 2021–2024 trading session is treated as the decision date for a separate USD
100,000 account:

1. The account begins with zero positions.
2. Historical observations before the decision date remain available only to construct the frozen
   causal v19 signal, 126-session covariance and lagged liquidity/volatility state.
3. The decision-date close produces the first v19 target.
4. The first position return and entry cost occur on the following session under the unchanged
   accounting convention.
5. The account follows v19's frozen 10-session rebalance schedule for 21 realized sessions.
6. At the 21st session close, every remaining position is liquidated and the modeled exit cost is
   deducted.
7. Cash earns zero. A separate same-trades diagnostic doubles transaction costs while leaving
   short borrow unchanged.

The experiment evaluates all start dates with 21 future sessions inside the frozen snapshot. This
produced 984 overlapping episodes. Because adjacent one-month observations are dependent, the
reported interval for the aggregate mean uses a fixed-seed 5,000-replication moving-block bootstrap
with 21-observation blocks.

## What remains frozen from v19

- the 45-ETF universe and data snapshot;
- 3/6/12-month skipped and volatility-normalized momentum;
- 200-session moving-average confirmation and 0.25 dead zone;
- train-only calibration slope;
- portfolio risk, factor, sleeve, turnover and liquidity limits;
- next-session accounting and the complete cost model;
- the 21-session holding horizon and final liquidation rule.

No starting month, starting year, calendar filter or parameter is selected from the results.

## Result and reproduction

The aggregate one-month distribution was positive, but mean results were negative for starts in
2021 and 2022. The frozen cross-year gate therefore failed and the correct status is
`V19_1_START_POINT_ROBUSTNESS_NOT_CONFIRMED`. This is a post-OOS diagnostic on an already opened
holdout, not another pristine test. See [the full report](V19_1_RESULT_REPORT.md).

Run the preliminary six-date check and then the frozen full experiment with:

```bash
python -m scripts.pilot_v19_1_start_points
python -m scripts.run_v19_1_start_point_robustness --workers 4
```

The governing frozen protocol is
[`docs/V19_1_START_POINT_PROTOCOL.md`](docs/V19_1_START_POINT_PROTOCOL.md).
