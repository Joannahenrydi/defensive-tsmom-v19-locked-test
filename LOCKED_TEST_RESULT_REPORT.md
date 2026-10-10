# v19 Locked-Test Result Report

## Decision

`V19_LOCKED_TEST_PASSED`

The frozen v19 defensive time-series momentum strategy passed all six gates committed before the
2021–2024 holdout was evaluated. This is a narrow survival result: the return remained positive,
but its economic strength was much weaker than in train and development. No refit is permitted and
paper/live orders remain disabled.

## Headline performance

| Evaluation | Net CAGR | Net Sharpe | Max DD | Worst month | Annual turnover |
|---|---:|---:|---:|---:|---:|
| Locked test, baseline | **0.51%** | **0.150** | **-11.03%** | **-2.92%** | **0.465×** |
| Same trades, 2× transaction cost | **0.50%** | **0.147** | **-11.03%** | **-2.92%** | **0.465×** |

The baseline returned 2.03% cumulatively over 1,005 sessions. Annualized volatility was 3.88%,
average gross exposure was 75.45%, average net exposure was +52.64%, realized beta to SPY was
0.172 and return correlation to SPY was 0.732.

## Frozen-gate outcome

| Gate | Result |
|---|---|
| Integrity, accounting, execution and risk budgets | PASS |
| Net CAGR > 0 | PASS |
| Net Sharpe > 0 | PASS |
| Max DD no worse than -20% | PASS |
| Frozen trades at 2× transaction cost: CAGR > 0 | PASS |
| Frozen trades at 2× transaction cost: Sharpe > 0 | PASS |

The source SHA-256 matched the v19 development freeze. The 45-name universe was exact, the frozen
train calibration digest reproduced, the slope differed by only floating-point rounding, no
numerical-boundary solution was used in the test, and additive asset contributions reconciled to
portfolio gross return within `2.61e-18`.

## What happened in the holdout

Calendar returns were +1.89% in 2021, **-8.93% in 2022**, +5.64% in 2023 and +4.08% in 2024. The
largest drawdown began after the 2021-12-27 peak, bottomed on 2022-10-20 at -11.03% and recovered on
2024-09-11. The strategy therefore survived the holdout, but recovery took almost three years.

The result still behaved as a concentrated risk-managed long portfolio:

- Long-book gross contribution: +3.05%; short-book contribution: -0.25%.
- Equity sleeve contribution: +4.34%; credit: -1.27%.
- SPY was the largest contributor at +4.34%; IEF was the largest detractor at -1.54%.
- The five largest absolute ETF contributions—SPY, IEF, LQD, BIL and HYG—represented **78.0%** of
  absolute contribution.
- Correction regimes with lagged SPY drawdown of 5–10% lost 2.45%, while normal and deeper-stress
  regimes were positive.

These diagnostics reinforce the development finding that v19 is closer to a defensive long trend
portfolio than a symmetric cross-asset CTA. The test does not support a claim of a strong or broadly
diversified trend premium: Sharpe fell from 1.210 in train and 0.927 in development to 0.150 in the
locked test, and performance remained concentrated in a few instruments.

## Research conclusion

The precommitted question was whether a positive net trend edge remained economically identifiable
outside 2008–2020. Under that deliberately minimal gate, the answer is yes. The magnitude is weak,
directional equity dependence remains material, and the 2022 loss shows the portfolio can struggle
when rates and credit trend exposure offset its equity gains.

The frozen result must be kept as observed. v19 cannot be repaired and rerun against 2021–2024.
Any concentration control, short-book change, alternative trend horizon or risk overlay would be a
new version requiring new prospective evidence.

