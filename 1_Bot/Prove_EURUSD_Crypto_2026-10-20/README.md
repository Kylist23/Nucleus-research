# Prove su EUR/USD e Bitcoin (20/10/2026)

Chieste dall'autore il 20/10/2026: rifare su EUR/USD e sul bitcoin tutte le prove del thread sull'oro (fase 1), poi provare strategie di altri repository di GitHub, da sole e con i filtri delle skill (fase 2). Regole e criteri registrati nel Manuale (capitolo 8) prima di ogni calcolo. Solo Python sui dati storici: nessun EA, nessun ordine, nessun conto. Cassaforte (dal 2023) intatta.

Risultato: 79 prove (32 su EUR/USD, 47 sul bitcoin), nessuna supera i criteri di Nucleus. Il riepilogo in euro per l'autore e' in `RIEPILOGO_ECONOMICO.md`.

## Contenuto

- `RIEPILOGO_ECONOMICO.md`: quanto hanno guadagnato e perso le prove, e cosa fare.
- `riepilogo_numeri.csv`: una riga per prova (79 righe). Risultati nelle unita' della prova (R o %) e in euro su 10.000 (senza costi, costi normali, costi doppi), peggior discesa in euro, drawdown, conto azzerato, risultato reinvestendo i guadagni, criteri (S/N nell'ordine: operazioni, costi doppi, acquisti e vendite, due periodi, drawdown) e verdetto.
- `Dati/`: candele. Fonti e licenze in `codice/fonti_fase2.md`.
  - `EURUSD_M15_2015-12_2022-03.csv` (fase 1) e `EURUSD_M15_2015-01_2022-03.csv` (fase 2, con tutto il 2015 per il riscaldamento degli indicatori): ora server (New York + 7 ore); i dati finiscono il 04/03/2022.
  - `BTCUSD_M5_2015-12_2022-12.csv` (fase 1, ora server) e `BTCUSD_M5_UTC_2015-01_2022-12.csv` (fase 2, ora UTC).
- `EURUSD/` e `BTC/`: per ogni prova le operazioni (CSV, una riga per operazione) e i risultati in testo (`*_risultati.txt`). `t7_backtest_expert/` contiene i rapporti della skill backtest-expert.
- `codice/`: i programmi, descritti qui sotto.

## Programmi

Si lanciano dentro `codice/` con `python3 <programma> <argomenti>`. Le skill esterne si leggono da una copia dei repository ai commit indicati in `codice/fonti_fase2.md` (agiprolabs/claude-trading-skills 981e1d7, tradermonty/claude-trading-skills cb0f3aa).

- `mercati.py`: dati e ipotesi sui costi (`load` per la fase 1, `load_fase2` per la fase 2).
- `ft_common.py`: indicatori in stile TA-Lib e simulatore alla freqtrade.
- `fase2_motore.py`: indicatori, filtri (a) e (b) e simulatore comune della fase 2.
- `test_fase2_motore.py`: prove del simulatore su candele inventate.
- Fase 1 (ogni programma va lanciato con `EURUSD` e con `BTC`):
  - `t1_c1_avvolgente.py EURUSD`: serie C1;
  - `t2_serie_e.py EURUSD E1` (poi `E2` e `CTRL`): serie E;
  - `t3_exit_strategies.py EURUSD <repo agiprolabs>/skills/exit-strategies/scripts/exit_simulator.py`: le 5 uscite;
  - `t4_martello_stockbee.py EURUSD <repo tradermonty>/skills/stockbee-exhaustion-hammer-screener/scripts/screen_exhaustion_hammer.py` e `t4b_martello_controllo.py EURUSD`: candela a martello;
  - `t5_freqtrade_futures.py EURUSD`: le tre strategie freqtrade che vendono anche;
  - `t6_FGH.py EURUSD 2_Nucleus_e_Blueprint/Dati_EURUSD/eur_usd_ecb_raw.csv`: serie F, G, H;
  - `t7_backtest_expert.py`: giudizio di backtest-expert (argomenti nell'intestazione del programma).
- Fase 2:
  - `t8_regime_detection.py EURUSD <repo agiprolabs>/skills/regime-detection/scripts/regime_backtest.py` (poi `BTC`): la strategia della skill regime-detection;
  - `t9_eurusd_repo.py <percorso regime_backtest.py>`: N1-N6 su EUR/USD, da sole e con il filtro (a);
  - `t10_btc_repo.py <percorso regime_backtest.py>`: K1-K8 e K2b sul bitcoin, da sole, con il filtro (a) e con il filtro (b).
- `t11_riepilogo.py`: ricalcola tutte le prove dai CSV e scrive `riepilogo_numeri.csv`.

Le regole di ogni strategia, i filtri e le regole comuni del simulatore sono scritti nell'intestazione di `t9_eurusd_repo.py`, `t10_btc_repo.py` e `fase2_motore.py`, e nel Manuale.
