# v19 Frozen Defensive TSMOM Strategy

This is the complete human-readable definition of the only trading strategy evaluated in this
repository. The executable source is [`strategy/v19.py`](strategy/v19.py); portfolio accounting and
optimization are implemented in
[`backtest/cross_asset_budget.py`](backtest/cross_asset_budget.py).

## Universe and research windows

- Universe: the frozen 45-ETF cross-asset set listed in `strategy/v19.py`.
- Train: 2008-01-02 through 2016-12-30.
- Development: 2017-01-03 through 2020-12-31.
- Locked test: 2021-01-04 through 2024-12-31.
- Starting NAV for cost and capacity calculations: USD 100,000.

The repository contains the frozen daily input snapshot at [`inputs/etf_daily.csv`](inputs/etf_daily.csv)
and its development freeze record at
[`inputs/v19_development_freeze.json`](inputs/v19_development_freeze.json). The locked-test runner
checks the file hash, train calibration slope and calibration digest before producing a result.

## Signal

For ETF \(i\), lookback \(h\in\{63,126,252\}\), and date \(t\), the skipped momentum component is

\[
M_{i,t,h}=\frac{\log P_{i,t-21}-\log P_{i,t-h}}
{\sigma_{i,t}^{60}\sqrt{h-21}}.
\]

The 60-session daily volatility is shifted one session, so only information already available at
the decision time is used. The composite absolute-momentum signal is

\[
M_{i,t}=\operatorname{clip}\left(0.25M_{i,t,63}+0.35M_{i,t,126}
+0.40M_{i,t,252},-3,3\right).
\]

It survives only when its direction agrees with the 200-session moving-average filter:

- positive momentum requires adjusted close above the moving average;
- negative momentum requires adjusted close below the moving average;
- otherwise the signal is zero.

Signals with absolute value below 0.25 are also set to zero. The confirmed signal is divided by
lagged annualized 60-session volatility. The resulting score is multiplied by the frozen
train-only calibration slope `6.537825607487585e-06`. No calibration is refit on development or
test observations.

An ETF becomes eligible only after 252 prior valid return observations and valid lagged liquidity
data. Missing held returns invalidate the run.

## Portfolio construction

Every 10 sessions, the strategy maximizes the frozen expected-return score net of modeled trading
and short-borrow costs, subject to the following constraints:

| Constraint | Frozen value |
|---|---:|
| Gross exposure | 100% |
| Single ETF absolute weight | 10% |
| Net exposure | 60% |
| Annual forecast volatility | 8% |
| Turnover per rebalance | 25% |
| Participation in 60-session median dollar volume | 0.10% |
| Covariance window | 126 sessions |
| Diagonal covariance shrinkage | 50% |

The implementation also applies the frozen factor caps and sleeve gross caps recorded in
`strategy/v19.py`. Long and short positions are both permitted. Unused capital remains cash and
earns zero in this test.

## Execution and costs

A target computed at session \(t\)'s close becomes the held portfolio for the following realized
session. The backtest therefore does not earn session \(t\)'s return using information first known
at that close. Costs are charged when the target becomes active:

- 1 bp half-spread;
- 1 bp slippage;
- square-root market-impact coefficient 0.10 using order participation and daily volatility;
- 1% annual borrow on short exposure;
- zero commission in the frozen configuration.

The 2× transaction-cost stress doubles realized spread, slippage and impact costs on the same
trades while leaving borrow unchanged.

## Locked result and reproduction

The strategy passed its prespecified minimal directional-survival gate on 2021–2024, with 0.51%
net CAGR, 0.150 Sharpe and -11.03% maximum drawdown. The result was weak and concentrated, and it
does not authorize paper or live orders. See [the full report](LOCKED_TEST_RESULT_REPORT.md).

Run the exact strategy and locked evaluation with:

```bash
python -m scripts.run_locked_test
```

The governing frozen protocol is
[`docs/V19_LOCKED_TEST_PROTOCOL.md`](docs/V19_LOCKED_TEST_PROTOCOL.md).
