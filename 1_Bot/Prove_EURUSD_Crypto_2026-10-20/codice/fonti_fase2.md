# Fonti della fase 2 (strategie di altri repository)

Letti il 20/10/2026 con `git show` su copie senza checkout. Dai repository si prendono solo le regole, riscritte in
pandas nei programmi `t9_*` e `t10_*`. L'unico codice esterno eseguito sono le funzioni di calcolo della skill
regime-detection (indicatori e strategia della prova 8). Nessun ordine, nessuna chiave, nessun conto.

| Strategia | Repository | Commit | Licenza | File letti | Cosa si usa |
|---|---|---|---|---|---|
| N1 inversione intraday | QuantConnect/Lean | de116c0 | Apache 2.0 | Algorithm.Python/Alphas/IntradayReversalCurrencyMarketsAlpha.py | regola |
| N2 Bollinger + RSI + filtro giornaliero | OptiFabian/forex-medium-frequency-trading | f8d008a | MIT | src/fxalgo/strategies/bollinger_rsi_confluence.py, bollinger_reversion.py, multi_timeframe.py, features/htf.py, volatility.py, momentum.py, scripts/build_htf_features.py, scripts/head_to_head.py | regola (configurazione "D k=2.0 rsi=30/70") |
| N3 HLHB | BabyPips (estratti di ricerca, sito non raggiungibile); confronto con freqtrade-strategies hlhb.py | f3340ce | GPL-3 (freqtrade) | user_data/strategies/hlhb.py | regola BabyPips, non verificata |
| N4 rottura di Londra | Samuel-Oyedeji/tradlysis | d847128 | nessuna | app/strategy/session_breakout.py, app/config/settings.py, app/technicals/indicators.py | solo la regola (il programma e' un bot con soldi veri) |
| N5 e K3 RSI2 di Connors | jesse-ai/example-strategies | 7c91e0a | MIT | RSI2/__init__.py | regola |
| N6 Dynamic Breakout II | QuantConnect/Tutorials | 4a34189 | Apache 2.0 | 04 Strategy Library/04 The Dynamic Breakout II Strategy/*.html | regola descritta nel testo |
| K1 Donchian 20 + media 200 | jesse-ai/example-strategies | 7c91e0a | MIT | Donchian/__init__.py | regola |
| K2 e K2b rottura di volatilita' | youtube-jocoding/pyupbit-autotrade | 8bb68a0 | nessuna | backtest.py, bitcoinAutoTradeWithMA.py | solo la regola (gli script comprano con chiavi Upbit) |
| K4 BbandRsi | freqtrade/freqtrade-strategies | f3340ce | GPL-3 | user_data/strategies/berlinguyinca/BbandRsi.py | regola |
| K5 SimpleBollinger | jesse-ai/example-strategies | 7c91e0a | MIT | SimpleBollinger/__init__.py | regola |
| K6 TradingView_RSI | jesse-ai/example-strategies | 7c91e0a | MIT | TradingView_RSI/__init__.py | regola |
| K7 Supertrend | freqtrade/freqtrade-strategies e freqtrade/technical | f3340ce, ce0e895 | GPL-3 | user_data/strategies/Supertrend.py, technical/indicators/supertrend.py | regola |
| K8 incrocio medie 50/200 | jesse-ai/example-strategies | 7c91e0a | MIT | SMACrossover/__init__.py | regola |
| Filtro (a) e prova (c) | agiprolabs/claude-trading-skills | 981e1d7 | MIT | skills/regime-detection/scripts/regime_backtest.py | funzioni eseguite cosi' come sono |
| Filtro (b) | tradermonty/claude-trading-skills | cb0f3aa | MIT | skills/crypto-regime-analyzer/scripts/calculators/btc_trend_calculator.py | regola del punteggio di tendenza, riscritta |
| Prova (d) | tradermonty/claude-trading-skills | cb0f3aa | MIT | skills/backtest-expert/scripts/evaluate_backtest.py | programma eseguito cosi' com'e' |

Convenzioni degli indicatori controllate nel codice: freqtrade usa TA-Lib (RSI, ATR e ADX di Wilder) e Bollinger di
qtpylib con deviazione standard campionaria; jesse usa jesse-rust (Bollinger con deviazione standard della
popolazione, Ichimoku con span_a e span_b calcolati su dati fino a 25 candele prima, senza vedere il futuro); il
supertrend di technical usa la media semplice del true range. Commit di riferimento: freqtrade/freqtrade 7ff17f5,
jesse-ai/jesse 4fcbcdd, jesse-ai/jesse-rust bab04ad, ta-lib-python ee40529.

## Dati

- EUR/USD M15: github.com/ejtraderLabs/historical-data, commit fbd29b3, licenza Apache 2.0. Per la fase 2 si usa
  `Dati/EURUSD_M15_2015-01_2022-03.csv`, stessa fonte e stessa conversione del file della fase 1 (le righe in
  comune sono identiche), con il 2015 in piu' solo per il riscaldamento degli indicatori.
- Bitcoin: minuto di Bitstamp da github.com/ff137/bitstamp-btcusd-minute-data, commit c711b69. Dati in licenza
  CC BY-SA 4.0, derivati da "Zielak (mczielinski), Bitcoin Historical Data, Kaggle". Per la fase 2 si usa
  `Dati/BTCUSD_M5_UTC_2015-01_2022-12.csv`, candele da 5 minuti in ora UTC dal 01/01/2015 al 31/12/2022 23:55
  (il 2015 solo per il riscaldamento). Il file di candele e' un'opera derivata e resta sotto CC BY-SA 4.0.
- Nessun dato dal 2023 in poi: la cassaforte resta intatta.
