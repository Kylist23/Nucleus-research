# Perché sono fallite le idee di Nucleus (tabella dei fallimenti)

Scritta il 21/10/2026, su suggerimento dei commenti di Reddit (r/algotrading). Nessun nuovo test: solo numeri già registrati, ricalcolati dai file citati.

Legenda delle cause:
- **Costi:** senza costi l'idea guadagna, con i costi doppi perde.
- **Nessun vantaggio:** perde già senza costi, oppure perde con i costi normali (quelli veri, una volta sola).
- **Lato:** acquisti o vendite in perdita.
- **Periodo:** 2016-2019 o 2020-2022 in perdita.
- **Rischio:** drawdown sopra il 10% o stop di emergenza.
- **Poche operazioni:** meno di 100.

"n.d." = il dato non è nei file disponibili (Da verificare nel Manuale).

## Oro (XAUUSD), 2016-2022: tentativi ufficiali e scremature

| Idea | Operazioni | Senza costi | Costi normali | Costi doppi | Acquisti / vendite (costi doppi) | 2016-19 / 2020-22 (costi doppi) | Cause | Fonte |
|---|---|---|---|---|---|---|---|---|
| A1 incrocio medie H1 | n.d. | n.d. | -505 euro (tester) | n.d. | n.d. | n.d. | Nessun vantaggio | `README.md` |
| A2 rottura 20 giorni, 5 mercati | 210 | n.d. | n.d. | -21 R | n.d. | n.d. | Nessun vantaggio | `README.md` |
| A3 momentum 12 mesi, 5 mercati | n.d. | n.d. | -1,07% in 13 anni | n.d. | n.d. | n.d. | Nessun vantaggio (1 mercato su 5 positivo) | `README.md` |
| B1 rottura e retest | 175 chiusure | n.d. | -2.023,89 euro (tester) | n.d. | -267 / -1.757 euro (costi normali) | stop di emergenza ad aprile 2018 | Nessun vantaggio, lato (vendite), rischio | `Risultati_test/B1_TESTER_XAUUSD.csv`, prime 351 righe |
| B2 effetto notte/giorno | 967 chiusure | n.d. | -1.975,17 euro (tester) | n.d. | -126 / -1.849 euro (costi normali) | stop di emergenza a novembre 2017 | Nessun vantaggio, lato (vendite), rischio | `Risultati_test/B2_v1.01_TESTER_XAUUSD.csv` |
| C1 candela avvolgente M15 | 1.379 | +16,7 R | -102,6 R | -221,8 R | -124,7 / -97,1 R | -134,5 / -87,3 R (tutti gli anni negativi) | Costi (vantaggio lordo minimo: +0,012 R a operazione) | `Scrematura_Python/screen_c1.py` |
| D1 tendenza 200 giorni con leva | 12 | 9.808 euro su 10.000 | 6.908 euro | 6.810 euro | -900 / -2.290 euro | stop al 40% nel 2017 | Nessun vantaggio, poche operazioni, rischio | `Report_raddoppio_2026-10-14.md` |
| E1 rottura 24 ore, trailing | 1.246 | +49,8 R | -12,3 R | -74,4 R | -8,0 / -66,4 R | -76,0 / +1,6 R | Costi, lato (vendite), periodo (2016-19), rischio (37%) | `Scrematura_Python/screen_e_risultati.txt` |
| E2 rottura 24 ore, uscita a fette | 896 | +97,3 R | +48,3 R | -0,8 R | +52,8 / -53,6 R | -16,0 / +15,2 R | Costi, lato (vendite), periodo (2016-19), rischio (17,8%) | come sopra |
| F1 apertura di New York | 785 | +5,0 R | -15,8 R | -36,6 R | -12,3 / -24,3 R | -19,5 / -17,1 R | Nessun vantaggio, rischio (19,1%) | `Scrematura_Python/screen_FGH_risultati.txt` |
| G1 oro dopo un movimento del dollaro | 414 | +6,1 R | +0,8 R | -4,6 R | -10,8 / +6,2 R | -7,5 / +2,9 R | Costi, lato (acquisti), periodo (2016-19) | come sopra |
| H1 rimbalzo dopo un giorno forte | 204 | -10,0 R | -13,3 R | -16,5 R | -10,4 / -6,1 R | -3,9 / -12,5 R | Nessun vantaggio | come sopra |
| Scrematura 09/10, idea 1: inversione dopo 3 giorni (D1) | 283 | n.d. | n.d. | -28,5 R | -14,0 / -14,5 R | -19,4 / -9,1 R | Nessun vantaggio (tutto negativo) | `Scrematura_Python/screen_b3.py` |
| Scrematura 09/10, idea 2: rottura del range asiatico | 1.716 | n.d. | n.d. | -57,2 R | -46,6 / -10,6 R | -57,0 / -0,2 R | Nessun vantaggio (tutto negativo) | come sopra |
| Scrematura 09/10, idea 3: ritorno alla media H1 | 1.075 | n.d. | n.d. | -172,0 R | -59,6 / -112,4 R | -101,2 / -70,8 R | Nessun vantaggio (tutto negativo) | come sopra |

Note sul calcolo:
- "Costi normali" per C1, E1, E2, F1, G1 e H1 = (senza costi + costi doppi) / 2. È esatto, perché nei programmi i costi sono proporzionali al moltiplicatore (`screen_c1.py` righe 85-86, `screen_e.py` riga 121, `screen_FGH.py` riga 68).
- B1 e B2 sono test MT5: il risultato del tester contiene già i costi normali (spread vero, swap, commissioni). Acquisti e vendite sono sommati dalle chiusure del CSV (Verificato oggi).
- Le tre idee del 09/10 sono state rieseguite oggi con lo stesso programma e gli stessi dati: i numeri sono quelli stampati da `screen_b3.py`, che calcola solo con i costi doppi.

## Cosa dicono le 15 idee sull'oro, tutte insieme

| Fino a dove regge l'idea | Quante | Quali |
|---|---|---|
| Perde già senza costi | 2 | D1, H1 |
| Guadagna senza costi, perde con i costi normali | 3 | C1, E1, F1 |
| Guadagna con i costi normali, perde solo con i costi doppi | 2 | E2 (+48,3 R), G1 (+0,8 R) |
| Perde con i costi normali (test MT5), risultato senza costi non disponibile | 3 | A1, B1, B2 |
| Perde, ma nei file c'è solo il risultato con i costi | 5 | A2, A3, le 3 scremature del 09/10 |

| Altro segnale | Quante | Dettaglio |
|---|---|---|
| Vendite in perdita | 11 su 12 con il dato | L'unica eccezione è G1, dove perdono gli acquisti (-10,8 R) e guadagnano le vendite (+6,2 R) |
| 2016-2019 in perdita | 9 su 9 con il dato | C1, E1, E2, F1, G1, H1 e le 3 scremature. È quasi sempre il periodo peggiore (eccezione: H1) |

Lezioni:
1. **La regola dei costi doppi ha deciso solo in 2 casi su 15** (E2 e G1). Almeno 8 idee su 15 perdono anche con i costi veri; per le altre 5 il dato non c'è. Il problema principale non è la severità sui costi: è che quasi nessuna idea aveva un vantaggio.
2. **Le vendite sull'oro perdono quasi sempre.** È coerente con un mercato salito molto nel periodo. Un'idea che guadagna solo con gli acquisti rischia di copiare "compra e tieni": va confrontata con quello, non promossa da sola.
3. **Il 2016-2019 è il periodo più difficile.** Le poche idee che guadagnano lo fanno soprattutto nel 2020 (E1 +34,1 R, E2 +29,7 R in quell'anno). Un solo anno buono non è un vantaggio.

## Campagna esplorativa su EUR/USD e Bitcoin (79 prove, non contano come tentativi)

Fonte: `Prove_EURUSD_Crypto_2026-10-20/riepilogo_numeri.csv`, colonna dei criteri (ricalcolato oggi).

| Criterio non superato | EUR/USD (32 prove) | Bitcoin (47 prove) |
|---|---|---|
| Meno di 100 operazioni | 8 | 8 |
| Negativa con i costi doppi | 31 | 23 |
| Acquisti o vendite in perdita (nel conteggio sono incluse le prove solo-acquisti: 10 su EUR/USD, 31 sul Bitcoin) | 31 | 46 |
| Un periodo in perdita | 31 | 35 |
| Drawdown sopra il 10% | 25 | 47 |
| Positiva senza costi, negativa con i costi doppi | 15 | 16 |
| Negativa già senza costi | 16 | 7 |
| Bocciata per un solo criterio | 1 (TrendFollowingStrategy: solo 10 operazioni) | 0 |

Lezioni: su EUR/USD metà delle prove perde già senza costi, quindi non c'è un vantaggio da proteggere. Sul Bitcoin tutte le 47 prove superano il 10% di drawdown: il limite di rischio, più dei costi, è la barriera.

## Conteggio di tutte le prove (per la correzione dei tentativi multipli)

- Oro: 12 tentativi ufficiali (A1-A3, B1-B2, C1, D1, E1-E2, F1, G1, H1) + 3 idee scremate il 09/10 = **15 idee**.
- Cripto (Ufficio Cripto): CR1 = **1 idea**.
- Prove esplorative EUR/USD e Bitcoin: **79**.
- Prove delle skill esterne sull'oro del 20/10 (`Prove_skill_esterne_2026-10-20/`): **non contate qui**, Da verificare quante sono.
- Varianti di controllo (stop x0,5 e x1,5, CTRL della Serie E, ecc.): non sono tentativi per le regole di Nucleus, ma fanno parte della storia della ricerca e vanno ricordate se un giorno un'idea passa.
