# v19.1 — Daily Starting-Point Robustness Protocol

Frozen after the prespecified six-date pilot and before the full daily starting-point grid. The
pilot produced six distinct 21-session net returns, so the full experiment is informative. This is
a post-OOS robustness diagnostic on the already opened 2021–2024 v19 holdout; it is not a second
pristine OOS test and cannot upgrade v19 to live-trading status.

## Frozen question

If a new USD 100,000 account starts the unchanged v19 strategy from cash on an arbitrary trading
day, is its following one-month net-return distribution consistently positive across 2021–2024?

## Frozen episode construction

- Candidate starting dates: every trading session from 2021-01-04 for which 21 future sessions
  exist in the frozen snapshot ending 2024-12-31.
- Each episode starts from zero positions.
- Historical observations before the start date may be used only to construct the already frozen
  causal v19 signal, 126-session covariance and 60-session ADV/volatility state.
- The start-date close produces the first target. Its position and transaction cost first affect
  the following session, matching the original next-session accounting.
- The account follows the unchanged 10-session rebalance schedule for 21 realized sessions.
- At the 21st session close, all positions are liquidated and the modeled exit transaction cost is
  deducted. Cash earns zero.
- The v19 universe, signal, train calibration, moving-average confirmation, dead zone, volatility
  scaling, risk budgets, turnover/liquidity limits and costs remain unchanged.
- A same-trades 2× transaction-cost result is computed for every episode; short borrow is unchanged.

## Pilot continuation rule

The six deterministic pilot dates were 2021-01-04, 2021-11-01, 2022-03-01, 2022-09-01,
2023-04-03 and 2024-01-02. Full-grid evaluation proceeds only because every episode completed and
more than one return was observed at 12 decimal places. Pilot returns choose no parameters and are
reported separately.

## Prespecified outputs

Report every episode, the mean/median/standard deviation, positive and loss rates, 5th/25th/75th/
95th percentiles, worst/best outcomes, maximum episode drawdown, turnover, exposure, transaction
and borrow costs. Report the same distribution by starting calendar year and month, plus cumulative
mean stability as the number of starting points grows.

Because adjacent 21-session windows overlap, naive episode-level t statistics are prohibited. A
fixed-seed moving-block bootstrap with 21-observation blocks and 5,000 resamples estimates the 95%
confidence interval of the mean liquidation-adjusted net return.

## Frozen robustness gate

`V19_1_START_POINT_ROBUSTNESS_CONFIRMED` requires all of the following:

1. at least 750 completed episodes, no failed episodes and no numerical-boundary solutions;
2. overall mean and median liquidation-adjusted return greater than zero;
3. at least 55% of episodes have positive liquidation-adjusted return;
4. every starting calendar year has positive mean and median return and at least 50% positive
   episodes;
5. the 21-observation block-bootstrap 95% lower bound for the mean is greater than zero;
6. under 2× transaction costs, overall mean and median remain greater than zero.

Otherwise the result is `V19_1_START_POINT_ROBUSTNESS_NOT_CONFIRMED`. This gate measures stability,
not whether every one-month episode is profitable. No v19 parameter may be changed in response.

