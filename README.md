# Nucleus: a beginner's trading research lab (looking for critical feedback)

**I am looking for criticism, not compliments.** I am a beginner in programming, finance and AI. This repository is my personal research log on automated trading. So far every trading idea I have tested has failed my own criteria. Before I spend more time, I would like experienced people to tell me where my method is wrong, weak or naive.

Nothing here is financial advice. Nothing here has ever traded real money, and nothing here should.

## What Nucleus is

- **The idea:** a small lab where I test trading ideas with strict, pre-written rules, mainly on gold (XAUUSD CFD) with MetaTrader 5 Expert Advisors (MQL5) and quick screening in Python.
- **The principle:** control and verifiability before autonomy and profit. AI assistants (mainly Claude) help me write code and analyse results. They do not trade. Most of the code in this repository was written by an AI assistant under my direction, and I reviewed the results with it.
- **Long-term goal (honestly, still far away):** a system of AI agents that helps with research and analysis. Today it is only Python scripts, MQL5 EAs and an AI assistant working in a chat.

## The rules I test against

These rules are written **before** each test and never changed after seeing the results.

1. **Criteria first.** Pass/fail criteria are written down, with a date, before the test runs.
2. **A locked hold-out ("the safe").** Data from 2023 to today is never used. Tests use 2016-2022 only. The hold-out may be used once, later, with thresholds written in advance.
3. **Costs paid twice.** A result must be positive with spread, commission and swap counted **double**.
4. **At least 100 trades.**
5. **Long and short both positive**, separately.
6. **Both sub-periods positive:** 2016-2019 and 2020-2022.
7. **Max relative drawdown under 10%.**
8. **Max 3 attempts per idea "series".** Any tweak to improve a result counts as a new attempt.
9. **Negative results are recorded**, not deleted.
10. **No real money.** EAs block real accounts in code. Going live would require at least 3 months on demo, and the decision would be mine, by hand.

The full procedure is in `4_Crescita_idee_e_possibilita/Skill/nucleus-test-ea/SKILL.md` (in Italian).

## Results so far

All numbers come from the files in this repository. All results are simulated (backtest or Python screening). No real money was involved.

### Gold (XAUUSD), 2016-2022: every idea rejected

| Series | Idea | Result | Source |
|---|---|---|---|
| A1 | Moving-average cross, H1 | -505 EUR, profit factor 0.84 | `1_Bot/README.md` |
| A2 | 20-day breakout, D1, 5 markets | -21 R over 210 trades | `1_Bot/README.md` |
| A3 | 12-month momentum, 5 markets, 2010-2022 | -1.07% in 13 years | `1_Bot/README.md` |
| B1 | Previous-day level break and retest | -2,023.89 EUR, emergency stop hit (10% drawdown), April 2018 | `2_Nucleus_e_Blueprint/Audit/Valutazione_generale_Nucleus_2026-10-18.md` |
| B2 | Gold night/day effect | -1,975.17 EUR, emergency stop hit, November 2017 | same review file |
| C1 | M15 engulfing candle with H1 trend, 1R target | 1,379 trades, +16.7 R without costs, -221.8 R with double costs | `1_Bot/Scrematura_Python/screen_c1.py` |
| D1 | 200-day trend, 25% vol target, max leverage 3 | 10,000 to 6,810 EUR with double costs | `1_Bot/Report_raddoppio_2026-10-14.md` |
| E1 | 24-hour breakout, 2.5 x ATR trailing exit | 1,246 trades, +49.8 R gross, -74.4 R double costs | `1_Bot/Scrematura_Python/screen_e_risultati.txt` |
| E2 | Same entry, partial exits at 2R/3R/5R | 896 trades, +97.3 R gross, -0.8 R double costs; shorts -53.6 R | same |
| F1 | New York open momentum | 785 trades, +5.0 R gross, -36.6 R double costs | `1_Bot/Scrematura_Python/screen_FGH_risultati.txt` |
| G1 | Gold after a 0.5% EUR/USD move | 414 trades, +6.1 R gross, -4.6 R double costs | same |
| H1 | Reversal after a 1 ATR day | 204 trades, -10.0 R gross, -16.5 R double costs | same |

Plus 3 ideas rejected in an earlier Python screen (details in `1_Bot/README.md`, in Italian).

**My current reading:** several ideas are slightly positive before costs and clearly negative after. With retail CFD costs on gold, a rule with a 1 USD target and a 1 USD stop needs to win about 68% of the time just to break even, because the median spread (0.18 USD) is paid twice (`1_Bot/Proposte/Serie_C_candele_proposta.md`). I would like to know if this reading is right.

### EUR/USD and Bitcoin campaign: 79 tests, 0 pass

On 20/10/2026 I re-ran the gold ideas, and rules taken from public GitHub repositories (freqtrade-strategies, jesse example strategies, QuantConnect, and others, listed with commits and licences in `1_Bot/Prove_EURUSD_Crypto_2026-10-20/codice/fonti_fase2.md`), on EUR/USD (32 tests) and Bitcoin (47 tests). None passed all criteria (`1_Bot/Prove_EURUSD_Crypto_2026-10-20/riepilogo_numeri.csv`, one row per test).

- EUR/USD: with normal costs 30 of 32 tests lose money.
- Bitcoin: 33 of 47 make money with normal costs, but almost only from the long side during a ~38x rise; shorts lose in 13 of 16 tests, and the best rules had drawdowns of 48% to 75%.

These were exploratory and did not count as official attempts.

### The only rule that passed: a slow, rebalanced portfolio (on paper)

Portfolio "C" (25% gold, 25% bonds, 25% cash, 25% equities), monthly data 2001-2022, after costs and taxes, price-only (no dividends): 10,000 EUR to 20,802 EUR, 3.4% a year, max drawdown 9.0%. It passes the criteria, but with obvious hindsight bias (gold rose a lot in that period). So it is being followed as a paper portfolio from November 2026, on data nobody has seen yet. Code in `portafoglio_carta/`, rules in `portafoglio_carta/docs/STRADA1_PORTAFOGLIO_CARTA.md` and `portafoglio_carta/docs/STRADA1_SPEC_TEST.md`. Source of the numbers: the general review in `2_Nucleus_e_Blueprint/Audit/Valutazione_generale_Nucleus_2026-10-18.md`.

## What I would like you to check

1. **Look-ahead bias.** Do any of the Python screens use information from the future? For example, the close of a candle that is not closed yet, a wrong `shift`, or ECB data used before its publication time.
2. **Cost model.** Are my cost assumptions realistic for a retail CFD account (spread, commission, swap)? Too high, too low? See `1_Bot/Scrematura_Python/costi_scalping.py` and `1_Bot/Prove_EURUSD_Crypto_2026-10-20/codice/mercati.py`.
3. **The criteria themselves.** Are they too strict, too loose, or simply the wrong ones? Is "costs paid twice" sensible?
4. **Multiple testing.** After about 15 ideas plus 79 exploratory tests, how should I correct for the number of attempts (Deflated Sharpe Ratio, White's Reality Check, something else)?
5. **The paper portfolio.** Is 3.4% a year with this much hindsight worth anything at all?
6. **Bugs in the simulators** (`1_Bot/Prove_EURUSD_Crypto_2026-10-20/codice/fase2_motore.py`, `ft_common.py`) or in the MQL5 EAs (`1_Bot/EA/`).
7. **Is the whole idea worth continuing** for a beginner, or should I stop?

Please be direct. "This is wrong because..." is exactly what I am looking for. Issues and comments on GitHub are welcome.

## What is NOT in this repository, and why

- **No price data.** Price files (CSV, XLSX, JSON) come from third parties (broker, Stooq, ECB, Bitstamp/Kaggle, ejtraderLabs) with their own licences, so I do not redistribute them. Sources are named in the code and in `fonti_fase2.md`. The scripts will not run without the data.
- **No trade logs** (one row per trade, with prices), for the same reason.
- **No personal data**, account details, broker settings or MetaTrader 5 settings.
- **No third-party code.** Rules from other repositories were rewritten; their code is not included.

## Folder map

| Folder | Contents |
|---|---|
| `1_Bot/` | Gold research: MQL5 EAs (`EA/`), Python screens (`Scrematura_Python/`), test register (`README.md`), reports |
| `1_Bot/Prove_EURUSD_Crypto_2026-10-20/` | EUR/USD and Bitcoin campaign: code, per-test summaries, economic summary |
| `1_Bot/Prove_skill_esterne_2026-10-20/` | Tests of external "skills" (exit strategies, freqtrade futures, hammer screener) |
| `2_Nucleus_e_Blueprint/` | Project description and the general review of 18/10/2026 |
| `4_Crescita_idee_e_possibilita/Skill/` | The fixed testing procedure (`nucleus-test-ea`) |
| `5_Ufficio_Cripto/` | Separate crypto track (one test, CR1, rejected) |
| `Esperimento_libero/` | "Can 100 EUR become 1,000?" style experiments. Spoiler: mostly ruin |
| `portafoglio_carta/` | Python package for data acquisition (ECB, Fed H.10), the portfolio backtest and the paper portfolio, with tests |

Most documents and code comments are in **Italian**. Feel free to comment in English.

## Status

- 20/10/2026: pause on new trading ideas until at least 20/01/2027. Focus on the paper portfolio and cleaning up.
- Real money: none, ever, so far. Profit and loss: 0 EUR.

## Licence

Code and documents are released under the MIT licence (see `LICENSE`): you may use, copy and modify them, keeping the copyright notice. The licence does not cover third-party price data, which is not included. Provided as is, with no warranty: this is not financial advice and nothing here is meant for trading real money.
