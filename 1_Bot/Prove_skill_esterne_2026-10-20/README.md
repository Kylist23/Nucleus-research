# Prove esplorative con skill esterne sull'oro (20/10/2026)

Chieste dall'autore senza la procedura nucleus-test-ea. NON sono tentativi Nucleus: nessuna di queste prove puo' portare una strategia in demo. Registrate nel Manuale (capitolo 8) prima di eseguirle.
Dati: `1_Bot/Dati/XAUUSD_M5_2016-2022.csv` (broker, 2016-2022). Cassaforte 2023-oggi intatta. Nessuna libreria installata: solo pandas e numpy gia' presenti.

## Fonti (lette, non installate)

| Repository | Commit | Skill usate | Soldi veri? |
|---|---|---|---|
| github.com/agiprolabs/claude-trading-skills (MIT) | 981e1d7 | exit-strategies (`exit_simulator.py`) | No: solo calcoli |
| github.com/tradermonty/claude-trading-skills (MIT) | cb0f3aa | stockbee-exhaustion-hammer-screener, backtest-expert | No: il filtro legge prezzi, backtest-expert fa solo conti |

## Risultati (file `risultati_*.txt`)

### 1. Le 5 uscite di exit-strategies, codice della skill senza modifiche (solo acquisti)

Entrata: rottura del massimo delle 24 ore su H1. Costi: spread (minimo 0,20 $) + swap stimato 3%/anno. Somma dei rendimenti % delle operazioni.

| Uscita | Operazioni | Senza costi | Costi x1 | Costi x2 | 2016-19 / 2020-22 (x2) |
|---|---|---|---|---|---|
| Trailing EMA 20 | 577 | +48,4% | +32,6% | +16,9% | +8,5% / +8,4% |
| Trailing ATR 2,5 | 579 | +31,7% | +15,8% | 0,0% | +3,1% / -3,2% |
| Stop fisso 10% | 175 | +26,9% | +6,3% | -14,2% | +8,4% / -22,6% |
| Uscita a fette | 175 | identica allo stop fisso | | | |
| Stop a tempo 50 barre | 303 | +10,3% | -9,1% | -28,5% | -10,1% / -18,4% |

- Lo stop fisso e l'uscita a fette danno lo stesso risultato: con parametri da criptovalute (stop al 10%, target al +20%) sull'oro stop e target non scattano quasi mai e ogni operazione finisce dopo 200 ore.
- Controllo con entrate a caso (20 prove, costi x2): trailing ATR mediana -15,2% (da -56,5% a +8,6%), trailing EMA mediana -17,2% (da -50,2% a +16,2%). Il trailing EMA con l'entrata a rottura (+16,9%) supera di poco la prova a caso migliore.
- Riferimento: comprare e tenere l'oro nello stesso periodo = +71,6%.

### 2. Candela a martello (stockbee-exhaustion-hammer-screener), solo acquisti

- Con le soglie della skill (pensate per le azioni): 3 segnali in 7 anni (-0,2 R con costi x2). Inutilizzabile sull'oro: il 97% dei giorni e' scartato perche' l'oro non recupera il 2% dal minimo in un giorno.
- Solo la forma della candela: 151 operazioni, -1,5 R senza costi, -21,4 R con costi x2; 2016-19 +2,0 R, 2020-22 -23,5 R.

### 3. Giudizio di backtest-expert (limite di drawdown impostato al 10% come Nucleus)

| Strategia | Punteggio | Decisione |
|---|---|---|
| Trailing EMA 20 | 71/100 | RISK_LIMIT_EXCEEDED (drawdown 17,9% senza leva) |
| Trailing ATR 2,5 | 65/100 | REJECT |
| Martello, solo forma | 59/100 | REJECT |
| Serie E2 (a fette) | 58/100 | REJECT |

### 4. Strategie che vendono anche allo scoperto (freqtrade-strategies, cartella futures)

Fonte: github.com/freqtrade/freqtrade-strategies, commit f3340ce, licenza GPL-3. Freqtrade non e' installato: regole ricopiate in pandas (`prova_freqtrade_futures.py`), valori predefiniti, leva tolta. Costi: spread + swap stimato (acquisti 3%/anno, vendite 1%/anno). Somma dei rendimenti % senza leva.

| Strategia | Operazioni (acquisti / vendite) | Senza costi | Costi x2 | Acquisti / vendite (x2) |
|---|---|---|---|---|
| FAdxSmaStrategy (H1, ADX + incrocio di medie) | 84 (42 / 42) | -6,0% | -10,0% | -4,3% / -5,7% |
| VolatilitySystem (3 ore, movimento oltre 2 x ATR) | 149 (77 / 72) | -24,9% | -56,4% | -11,1% / -45,3% |
| TrendFollowingStrategy (M5, EMA 20 + OBV) | 21 (9 / 12) | +1,3% | -27,2% | +14,8% / -42,1% |

- In tutte e tre le vendite perdono: nel 2016-2022 l'oro e' salito del 71,6%, e vendere va contro questa salita.
- TrendFollowingStrategy fa solo 21 operazioni in 7 anni: la sua regola di uscita scatta di rado e le posizioni restano aperte per settimane (e' cosi' nell'originale).
- Candele + vendite: nessun repository aperto trovato che lo faccia sull'oro con codice leggibile (solo script a pagamento o protetti su TradingView e cTrader). Le strategie a candele di freqtrade-strategies (Strategy002, PatternRecognition) comprano soltanto. Nucleus l'ha gia' provato: Serie C1, candela avvolgente nei due versi con filtro di tendenza, -221,8 R con costi doppi.

## Repository visti ma non provati

- `mt5-robot-tester` (tradermonty): prova in serie molti EA nello Strategy Tester. Funziona solo su Windows (l'autore usa MT5 su Mac); ottimizza i parametri del +-50% e sceglie i migliori, cioe' il contrario delle regole Nucleus (rischio di risultati trovati per caso); avverte che puo' "svegliare" e chiudere un terminale collegato a un conto reale. Non usato.
- `backtesting.py`, `vectorbt`, `freqtrade`: richiedono installazione di librerie; non installate senza il sì dell'autore.
