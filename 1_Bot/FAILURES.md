# Why each Nucleus idea failed

Written on 21/10/2026 after feedback on r/algotrading. No new tests: only numbers already recorded, recomputed from the cited files. Italian version: `Tabella_fallimenti.md`.

"n/a" = the figure is not in the available files. R = multiples of the initial risk (stop distance). "Normal costs" = real costs counted once; "double costs" = the Nucleus stress rule.

## Gold (XAUUSD), 2016-2022: official attempts and early screens

| Idea | Trades | No costs | Normal costs | Double costs | Long / short (double costs) | 2016-19 / 2020-22 (double costs) | Why it failed | Source |
|---|---|---|---|---|---|---|---|---|
| A1 MA cross H1 | n/a | n/a | -505 EUR (tester) | n/a | n/a | n/a | No edge | `README.md` |
| A2 20-day breakout, 5 markets | 210 | n/a | n/a | -21 R | n/a | n/a | No edge | `README.md` |
| A3 12-month momentum, 5 markets | n/a | n/a | -1.07% in 13 years | n/a | n/a | n/a | No edge (1 market of 5 positive) | `README.md` |
| B1 break and retest | 175 closes | n/a | -2,023.89 EUR (tester) | n/a | -267 / -1,757 EUR (normal costs) | emergency stop, April 2018 | No edge, shorts, risk | `Risultati_test/` (trade log not published) |
| B2 night/day effect | 967 closes | n/a | -1,975.17 EUR (tester) | n/a | -126 / -1,849 EUR (normal costs) | emergency stop, November 2017 | No edge, shorts, risk | same |
| C1 M15 engulfing | 1,379 | +16.7 R | -102.6 R | -221.8 R | -124.7 / -97.1 R | -134.5 / -87.3 R (every year negative) | Costs (gross edge only +0.012 R per trade) | `Scrematura_Python/screen_c1.py` |
| D1 200-day trend with leverage | 12 | 9,808 EUR from 10,000 | 6,908 EUR | 6,810 EUR | -900 / -2,290 EUR | 40% stop hit in 2017 | No edge, too few trades, risk | `Report_raddoppio_2026-10-14.md` |
| E1 24h breakout, trailing | 1,246 | +49.8 R | -12.3 R | -74.4 R | -8.0 / -66.4 R | -76.0 / +1.6 R | Costs, shorts, 2016-19, drawdown 37% | `Scrematura_Python/screen_e_risultati.txt` |
| E2 24h breakout, partial exits | 896 | +97.3 R | +48.3 R | -0.8 R | +52.8 / -53.6 R | -16.0 / +15.2 R | Double costs, shorts, 2016-19, drawdown 17.8% | same |
| F1 New York open | 785 | +5.0 R | -15.8 R | -36.6 R | -12.3 / -24.3 R | -19.5 / -17.1 R | No edge, drawdown 19.1% | `Scrematura_Python/screen_FGH_risultati.txt` |
| G1 gold after a USD move | 414 | +6.1 R | +0.8 R | -4.6 R | -10.8 / +6.2 R | -7.5 / +2.9 R | Double costs, longs, 2016-19 | same |
| H1 rebound after a big day | 204 | -10.0 R | -13.3 R | -16.5 R | -10.4 / -6.1 R | -3.9 / -12.5 R | No edge | same |
| Screen 09/10 #1: 3-day reversal (D1) | 283 | n/a | n/a | -28.5 R | -14.0 / -14.5 R | -19.4 / -9.1 R | No edge | `Scrematura_Python/screen_b3.py` |
| Screen 09/10 #2: Asian range breakout | 1,716 | n/a | n/a | -57.2 R | -46.6 / -10.6 R | -57.0 / -0.2 R | No edge | same |
| Screen 09/10 #3: H1 mean reversion | 1,075 | n/a | n/a | -172.0 R | -59.6 / -112.4 R | -101.2 / -70.8 R | No edge | same |

Normal costs for C1, E1, E2, F1, G1 and H1 = (no costs + double costs) / 2. This is exact, because costs in the scripts scale linearly with the multiplier.

## Summary of the 15 gold ideas

| How far the idea holds | Count | Ideas |
|---|---|---|
| Loses even without costs | 2 | D1, H1 |
| Profitable without costs, loses with normal costs | 3 | C1, E1, F1 |
| Profitable with normal costs, loses only with double costs | 2 | E2 (+48.3 R), G1 (+0.8 R) |
| Loses with normal costs (MT5 test), no-cost figure not available | 3 | A1, B1, B2 |
| Loses, only the after-cost figure is recorded | 5 | A2, A3, the three 09/10 screens |

- Shorts lose in 11 of the 12 ideas with the figure (exception: G1).
- 2016-2019 is negative in 9 of 9 ideas with the figure.

Lessons:
1. The double-cost rule decided only 2 of 15 cases (E2 and G1). At least 8 of 15 lose with real costs. The main problem is not cost severity: almost no idea had an edge.
2. Shorts on gold almost always lose, consistent with a strongly rising market. A long-only idea must be compared with buy-and-hold, not approved on its own.
3. The few ideas that make money do it mostly in 2020 (E1 +34.1 R, E2 +29.7 R that year). One good year is not an edge.

## Exploratory EUR/USD and Bitcoin campaign (79 tests, not official attempts)

Source: `Prove_EURUSD_Crypto_2026-10-20/riepilogo_numeri.csv`.

| Criterion failed | EUR/USD (32) | Bitcoin (47) |
|---|---|---|
| Fewer than 100 trades | 8 | 8 |
| Negative with double costs | 31 | 23 |
| Long or short negative (includes long-only tests: 10 EUR/USD, 31 BTC) | 31 | 46 |
| One sub-period negative | 31 | 35 |
| Drawdown above 10% | 25 | 47 |
| Positive without costs, negative with double costs | 15 | 16 |
| Negative even without costs | 16 | 7 |
| Failed on one criterion only | 1 (TrendFollowingStrategy: 10 trades) | 0 |

## Full search history (for multiple-testing corrections)

- Gold: 15 ideas (12 official attempts + 3 early screens).
- Crypto track: 1 idea (CR1).
- Exploratory EUR/USD and Bitcoin: 79 tests.
- External-skill tests on gold (`Prove_skill_esterne_2026-10-20/`): not counted here yet.
- Control variants (stop x0.5 and x1.5, Series E control run): not attempts under Nucleus rules, but part of the search history.
