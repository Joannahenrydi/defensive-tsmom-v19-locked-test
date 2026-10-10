# v19 Locked-Test Protocol

Frozen before the 2021–2024 holdout is evaluated. This protocol authorizes one read of the
pre-existing 45-ETF snapshot and one evaluation of the frozen v19 defensive time-series momentum
strategy. No parameter, signal, universe, calibration, portfolio, execution or cost choice may be
changed after the result is observed.

## Research windows and frozen inputs

- Train: 2008-01-02 through 2016-12-30.
- Reused development audit: 2017-01-03 through 2020-12-31.
- Locked test: 2021-01-04 through 2024-12-31.
- Strategy freeze: `v19-development-freeze-20260927` in the source research repository.
- Source snapshot SHA-256: `82347fef112a5f04dc2b5accf947f362eefe1a0a89f1c59bf143a369ab63e32e`.
- Frozen train calibration slope: `6.537825607487585e-06`.
- Frozen train calibration digest: `d59984125ff01d469e8b75ded4e674f6a8708b1f066b92d9ce8ef5a744ab9122`.

The evaluator must reproduce the train calibration slope and digest before reporting the holdout.
It must also verify the source hash, exact test boundary, complete 45-name universe, causal signal
construction and absence of non-finite held returns.

## Frozen strategy

The strategy is the sole v19 candidate: 3/6/12-month volatility-normalized absolute momentum with
weights 25%/35%/40%, a 21-session skip, 200-session directional moving-average confirmation, 0.25
dead zone and 60-session trailing volatility. Portfolio construction remains frozen at a 10-session
rebalance, 8% annual volatility cap, 100% gross cap, 10% name cap, 60% net cap, 25% turnover cap,
0.10% ADV participation and the recorded factor/sleeve budgets. Costs remain 1 bp half-spread,
1 bp slippage, square-root impact coefficient 0.10 and 1% annual short borrow.

No candidate grid, parameter search, benchmark-relative selection, re-entry rule, concentration
repair or post-result refit is permitted.

## Primary locked-test gate

The frozen candidate passes only if every condition below holds on 2021-01-04 through 2024-12-31:

1. the backtest completes without accounting, execution, causality, input-integrity or risk-budget
   failure;
2. net CAGR is greater than zero;
3. net Sharpe is greater than zero;
4. maximum drawdown is no worse than -20%;
5. the same frozen trades retain positive CAGR and positive Sharpe when realized transaction costs
   are doubled while borrow cost is unchanged.

The gate does not require Sharpe above 0.50, each calendar year to be positive, or both long and
short books to make money. Passing is historical evidence only and cannot authorize paper or live
orders.

## Prespecified diagnostics

The one run must report net/gross performance, turnover, costs, average gross/net exposure,
calendar-year returns, long/short contributions, sleeve and ETF contributions, top-five absolute
contribution concentration, lagged SPY drawdown-regime contribution, realized beta to SPY and the
largest drawdown episodes. These diagnostics explain the result and cannot alter the primary gate.

## Decision and contamination rule

- Pass: `V19_LOCKED_TEST_PASSED`.
- Fail: `V19_LOCKED_TEST_FAILED`.
- `orders_allowed` remains `false` in either case.
- The test is read once. After results are written, v19 cannot be modified and rerun against this
  holdout. Any later strategy change must receive a new version and new prospective evidence.

