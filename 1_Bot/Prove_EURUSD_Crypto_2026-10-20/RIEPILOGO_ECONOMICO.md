# EUR/USD e Bitcoin: quanto hanno guadagnato e quanto hanno perso le prove

20 ottobre 2026. Tutte le prove fatte nel thread sull'oro, rifatte su EUR/USD e sul bitcoin, piu' le strategie di altri repository di GitHub, da sole e insieme ai filtri delle skill. Solo prove sui dati storici: nessun EA scritto, nessuna operazione aperta, nessun conto toccato. Per le criptovalute ho usato il bitcoin, la piu' grande e quella con lo storico piu' lungo.

## In breve

- **EUR/USD: lascia perdere.** 32 prove, nessuna supera i criteri di Nucleus. Con i costi normali 30 su 32 perdono soldi, e una prova perde in media 1.198 euro su un conto da 10.000 euro in 6 anni. Anche senza costi meta' delle prove guadagna e meta' perde, come tirando una moneta: non c'e' un vantaggio da migliorare.
- **Bitcoin: lascia perdere per Nucleus.** 47 prove, nessuna supera i criteri. Molte guadagnano (33 con i costi normali), ma quasi solo grazie agli acquisti, perche' dal 2016 al 2022 il prezzo del bitcoin si e' moltiplicato per 38. Quando le regole vendono per guadagnare sul ribasso, perdono in 13 prove su 16. Le cinque regole migliori, reinvestendo i guadagni, hanno avuto discese del conto tra il 48% e il 75% (Nucleus accetta al massimo il 10%) e devono la maggior parte del guadagno, dal 64% all'88%, a 3 sole operazioni, quasi tutte del 2017 e del 2020.
- **Si puo' migliorare?** Non con ritocchi: cambiare i parametri guardando questi risultati vorrebbe dire adattare le regole al passato.
- **Cosa fare:** chiudere EUR/USD e bitcoin per Nucleus, senza altro lavoro. Anche un investimento lento sul bitcoin, solo in acquisto, e' gia' stato provato il 17/10/2026 (CR1, Ufficio Cripto) ed e' stato bocciato per un calo massimo del 67%: le prove di oggi dicono la stessa cosa. Resta valida la pausa che hai deciso oggi: nessuna nuova idea di trading fino al 20/01/2027 almeno.

## Come leggere i numeri

- Ogni prova parte da un conto di 10.000 euro.
- Periodo: EUR/USD dal 4 gennaio 2016 al 4 marzo 2022 (circa 6 anni: i dati gratuiti finiscono li'); bitcoin dal 1 gennaio 2016 al 31 dicembre 2022 (7 anni). I dati dal 2023 in poi, la cassaforte, non sono stati toccati.
- Quanto si punta:
  - nelle prove "a rischio fisso" (serie Nucleus C, E, F, G, H e candela a martello) ogni operazione rischia 50 euro, cioe' lo 0,5% del conto, fino allo stop;
  - in tutte le altre ogni operazione usa 10.000 euro, senza leva: un guadagno dell'1% vale 100 euro.
- Nelle tabelle la puntata resta sempre la stessa e i guadagni non vengono reinvestiti, cosi' ogni prova pesa uguale. Il confronto reinvestendo tutto e' nella parte sul bitcoin.
- Costi normali: spread e commissioni, piu' il costo per tenere la posizione aperta di notte (swap), stimati in modo prudente:
  - EUR/USD: 1,5 pip a operazione; swap 2,5% l'anno sugli acquisti e 0,5% sulle vendite;
  - bitcoin: 0,20% a operazione; finanziamento 10% l'anno sugli acquisti e 5% sulle vendite.
- Costi doppi: gli stessi costi pagati due volte. E' il metro di Nucleus, per stare sul sicuro.
- Peggior discesa: la perdita piu' grande dal punto piu' alto del conto, in euro, con i costi doppi.
- Azzerato: a un certo punto le perdite hanno superato i 10.000 euro del conto. Nella realta' la prova si sarebbe fermata li'.
- "+ filtro regime": la stessa regola, ma opera solo quando la skill regime-detection dice che il mercato e' adatto (in tendenza per le regole di tendenza, laterale e calmo per quelle di ritorno alla media).
- "+ filtro tendenza" (solo bitcoin): compra solo quando il punteggio di tendenza del bitcoin della skill crypto-regime-analyzer e' almeno 55 su 100, e vende solo quando e' al massimo 45.
- I 5 criteri di Nucleus, scritti prima di guardare i dati, tutti obbligatori:
  1. almeno 100 operazioni;
  2. in guadagno con i costi doppi;
  3. acquisti e vendite entrambi in guadagno;
  4. in guadagno sia nel 2016-2019 sia nel 2020-2022;
  5. discesa massima del conto sotto il 10%, reinvestendo i guadagni.

## Quanto hanno guadagnato e quanto hanno perso

Ogni prova ha il suo conto da 10.000 euro. Un conto azzerato conta come -10.000 euro.

| | EUR/USD | Bitcoin |
|---|---|---|
| Prove fatte | 32 | 47 |
| Prove che superano tutti i criteri di Nucleus | 0 | 0 |
| Prove in guadagno con i costi normali | 2 | 33 |
| Prove in perdita con i costi normali | 30 | 14 |
| Guadagno di tutte le prove in guadagno (costi normali) | +4.109 euro | +909.756 euro |
| Perdita di tutte le prove in perdita (costi normali) | -42.445 euro | -84.667 euro |
| Risultato medio di una prova, costi normali | -1.198 euro | +17.555 euro |
| Risultato medio di una prova, costi doppi | -2.465 euro | +8.713 euro |
| Prova migliore, costi normali | +3.535 euro (TrendFollowingStrategy, 10 operazioni) | +87.359 euro (Skill regime-detection: medie 10/30 giornaliere, 31 operazioni) |
| Prova peggiore, costi normali | -5.222 euro (C1 candela avvolgente M15 con tendenza H1) | conto azzerato (5 prove) |
| Prove in guadagno con i costi doppi | 1 | 24 |
| Conti azzerati con i costi doppi | 1 | 10 |
| Comprare e tenere nello stesso periodo (solo prezzo, senza costi) | +91 euro | +370.988 euro |

Attenzione al confronto con comprare e tenere: e' una sola posizione che cresce su se stessa, mentre nelle prove la puntata resta sempre di 10.000 euro. Il confronto alla pari, reinvestendo i guadagni, e' nella parte sul bitcoin: li' la regola migliore arriva a 665.390 euro con i costi normali, contro 380.988 euro di comprare e tenere bitcoin veri.

## EUR/USD

- La migliore e' TrendFollowingStrategy (freqtrade-strategies): +3.535 euro con i costi normali, ma con 10 operazioni in 6 anni. Sono troppo poche per distinguerla dalla fortuna: per questo non supera il criterio 1.
- La migliore con molte operazioni e' N2 (Bollinger e RSI con il regime giornaliero, dal repository di OptiFabian): 1.017 operazioni, +574 euro in 6 anni con i costi normali, cioe' circa 90 euro l'anno su 10.000. Con i costi doppi diventa -825 euro.
- Le serie di Nucleus (C, E, F, G, H) perdono tutte, come sull'oro. La serie E con il trailing (E1) azzera il conto con i costi doppi.
- Prima dei costi il totale delle 32 prove e' quasi zero (+2.145 euro, 67 euro a prova in 6 anni). Poi i costi trasformano quasi tutto in perdita.
- Il filtro della skill regime-detection fa perdere meno in 4 regole su 6, soprattutto perche' fa operare molto meno (per esempio N2 passa da 1.017 a 56 operazioni, N5 da 534 a 86), non perche' sceglie le operazioni buone: in N3 e N6 fa perdere di piu', e con i costi doppi tutte restano in perdita.
- Riferimento: comprare e tenere l'euro contro il dollaro nello stesso periodo da' +91 euro (+0,9%) prima dei costi, con una discesa massima del 15%. Pagando lo swap stimato sugli acquisti (2,5% l'anno) sarebbero circa -1.350 euro.

Tutte le prove su EUR/USD, dalla migliore alla peggiore con i costi normali (euro su un conto da 10.000, puntata fissa):

| Prova | Fonte | Operazioni | Senza costi | Costi normali | Costi doppi | Peggior discesa | Criteri superati |
|---|---|---:|---:|---:|---:|---:|---:|
| TrendFollowingStrategy | freqtrade-strategies | 10 | +4.167 | +3.535 | +2.903 | 482 | 4 su 5 |
| N2 Bollinger + RSI + regime giornaliero | OptiFabian | 1.017 | +1.973 | +574 | -825 | 1.121 | 1 su 5 |
| N2 Bollinger + RSI + regime giornaliero + filtro regime | OptiFabian + regime-detection | 56 | +48 | -31 | -110 | 139 | 1 su 5 |
| N5 RSI2 di Connors + filtro regime | jesse + regime-detection | 86 | +76 | -64 | -205 | 530 | 1 su 5 |
| H rimbalzo del giorno dopo | Nucleus (serie H) | 192 | -68 | -285 | -502 | 673 | 2 su 5 |
| Uscita: stop fisso 10% | agiprolabs exit-strategies | 157 | +1.196 | -294 | -1.785 | 2.435 | 1 su 5 |
| Uscita: a fette | agiprolabs exit-strategies | 157 | +1.196 | -294 | -1.785 | 2.435 | 1 su 5 |
| FAdxSmaStrategy | freqtrade-strategies | 74 | -199 | -324 | -450 | 550 | 1 su 5 |
| N3 HLHB (medie 5/10 + RSI + ADX) | BabyPips | 412 | +400 | -379 | -1.157 | 2.081 | 1 su 5 |
| F apertura di New York | Nucleus (serie F) | 297 | +48 | -423 | -894 | 1.007 | 2 su 5 |
| Skill regime-detection: adattiva giornaliera | agiprolabs regime-detection | 23 | +143 | -517 | -1.177 | 1.350 | 0 su 5 |
| G dollaro BCE | Nucleus (serie G) | 339 | -276 | -585 | -894 | 929 | 2 su 5 |
| Skill regime-detection: adattiva su H1 | agiprolabs regime-detection | 520 | +459 | -667 | -1.792 | 2.235 | 1 su 5 |
| N6 Dynamic Breakout II | QuantConnect Tutorials | 35 | -305 | -689 | -1.073 | 1.713 | 0 su 5 |
| N1 Inversione intraday + filtro regime | QuantConnect Lean + regime-detection | 287 | -316 | -691 | -1.066 | 1.088 | 1 su 5 |
| Uscita: trailing ATR 2,5 | agiprolabs exit-strategies | 533 | +474 | -721 | -1.917 | 2.221 | 1 su 5 |
| N6 Dynamic Breakout II + filtro regime | QuantConnect Tutorials + regime-detection | 34 | -461 | -840 | -1.218 | 1.889 | 0 su 5 |
| Uscita: trailing EMA 20 | agiprolabs exit-strategies | 525 | +318 | -857 | -2.032 | 2.168 | 1 su 5 |
| Uscita: stop a tempo 50 candele | agiprolabs exit-strategies | 267 | +351 | -1.015 | -2.380 | 2.875 | 1 su 5 |
| N5 RSI2 di Connors | jesse | 534 | -153 | -1.060 | -1.967 | 2.132 | 1 su 5 |
| N3 HLHB (medie 5/10 + RSI + ADX) + filtro regime | BabyPips + regime-detection | 320 | -488 | -1.096 | -1.704 | 1.862 | 1 su 5 |
| N1 Inversione intraday | QuantConnect Lean | 1.596 | +914 | -1.185 | -3.285 | 3.404 | 1 su 5 |
| Skill regime-detection: medie 10/30 su H1 | agiprolabs regime-detection | 657 | +342 | -1.285 | -2.912 | 3.322 | 1 su 5 |
| Skill regime-detection: medie 10/30 giornaliere | agiprolabs regime-detection | 34 | -597 | -1.374 | -2.152 | 2.152 | 0 su 5 |
| N4 Rottura di Londra + filtro regime | tradlysis + regime-detection | 891 | -476 | -1.646 | -2.815 | 3.252 | 1 su 5 |
| Candela a martello (solo forma) | tradermonty stockbee | 112 | -1.087 | -1.943 | -2.799 | 2.799 | 1 su 5 |
| N4 Rottura di Londra | tradlysis | 1.159 | -764 | -2.285 | -3.806 | 4.232 | 1 su 5 |
| VolatilitySystem | freqtrade-strategies | 117 | -2.193 | -3.162 | -4.130 | 4.351 | 1 su 5 |
| Controllo della serie E (target 2R) | Nucleus (serie E) | 1.146 | +551 | -4.046 | -8.643 | 8.834 | 1 su 5 |
| E2 rottura di 24 ore con uscita a fette | Nucleus (serie E) | 827 | -901 | -4.471 | -8.042 | 8.297 | 1 su 5 |
| E1 rottura di 24 ore con trailing | Nucleus (serie E) | 1.231 | -60 | -4.994 | azzerato | tutto il conto | 1 su 5 |
| C1 candela avvolgente M15 con tendenza H1 | Nucleus (serie C) | 637 | -2.167 | -5.222 | -8.277 | 8.277 | 1 su 5 |

Le prove "Uscita: ..." usano tutte la stessa entrata (rottura del massimo delle 24 ore, solo acquisti) e cambiano solo il modo di uscire (skill exit-strategies). Stop fisso 10% e uscita a fette danno lo stesso risultato perche', come sull'oro, stop e target non scattano mai e ogni operazione si chiude dopo 200 candele. Le prove "Skill regime-detection" usano la strategia della skill stessa (incrocio delle medie 10/30, fisso o adattato al regime), solo acquisti.

## Bitcoin

- Il guadagno viene quasi tutto dagli acquisti: il bitcoin e' passato da 434 dollari (1 gennaio 2016) a 16.528 dollari (31 dicembre 2022), 38 volte tanto. Nelle 16 prove che vendono anche, la parte delle vendite perde in 13.
- Le prove che solo comprano non possono superare il criterio 3 (acquisti e vendite entrambi in guadagno).
- Le cinque regole migliori (le prime cinque regole nel confronto qui sotto) seguono la tendenza lenta: l'incrocio delle medie 50/200 (K8) e la rottura del canale di Donchian a 20 periodi con la media 200 (K1), ciascuna da sola e con il filtro tendenza, e le medie 10/30 giornaliere della skill regime-detection. Pero':
  - reinvestendo i guadagni, le discese del conto vanno dal 48% al 75% (Nucleus accetta il 10%);
  - fanno poche operazioni, da 31 a 115 in 7 anni, e 3 sole operazioni fanno dal 64% all'88% di tutto il guadagno, quasi tutte nel 2017 e alla fine del 2020;
  - le operazioni aperte nel 2021-2022 sono in perdita in tutte e cinque.
- Le regole veloci, che entrano ed escono in poche ore o pochi giorni (RSI2 di Connors, TradingView_RSI, BbandRsi, la candela avvolgente C1, la serie F), guadagnano troppo poco per operazione rispetto ai costi: l'RSI2, per esempio, guadagna in media lo 0,14% a operazione prima dei costi e ne paga lo 0,20%. Con i costi doppi perdono tutte e 11 le prove di questo tipo, e 7 azzerano il conto.
- Il filtro tendenza (skill crypto-regime-analyzer) aiuta: migliora 6 regole su 9 (in K3 e K6 il conto si azzera comunque con i costi doppi) e riduce la discesa in tutte. Ma la discesa piu' piccola resta del 48%.
- Il filtro regime (skill regime-detection) fa perdere meno alle regole di ritorno alla media, perche' le fa operare molto meno, e peggiora 5 regole di tendenza su 6.

### Confronto con comprare e tenere, reinvestendo tutto

Qui ogni operazione usa tutto il conto, guadagni compresi, come succede tenendo il bitcoin. Quanto diventano 10.000 euro dal 2016 al 2022:

| Come | Operazioni | Costi normali | Costi doppi | Discesa massima (costi doppi) |
|---|---:|---:|---:|---:|
| Comprare bitcoin veri e tenerli, senza costo notturno | 1 | 380.988 | 380.988 | 83% |
| Comprare e tenere un CFD sul bitcoin, pagando il finanziamento notturno | 1 | circa 189.100 | circa 93.900 | 86% |
| Skill regime-detection: medie 10/30 giornaliere | 31 | 665.390 | 481.300 | 56% |
| K8 Incrocio medie 50/200 + filtro tendenza | 65 | 347.730 | 226.320 | 59% |
| K1 Donchian 20 + media 200 + filtro tendenza | 57 | 194.570 | 140.060 | 48% |
| K1 Donchian 20 + media 200 | 80 | 164.350 | 105.480 | 62% |
| K8 Incrocio medie 50/200 | 115 | 209.950 | 104.200 | 75% |
| K1 Donchian 20 + media 200 + filtro regime | 76 | 128.770 | 85.040 | 64% |

- Comprare bitcoin veri e tenerli 7 anni: 10.000 euro diventano 380.988 euro, ma passando per due crolli: da 442.298 a 73.292 euro tra dicembre 2017 e dicembre 2018 (-83%), e da 1.557.305 a 363.423 euro tra novembre 2021 e novembre 2022 (-77%).
- Le prove pagano i costi di un CFD, compreso il finanziamento notturno. A parita' di costi il confronto giusto e' con la seconda riga: tenere un CFD per 7 anni avrebbe piu' che dimezzato il risultato. Contro quella riga fanno meglio quattro delle cinque regole migliori con i costi normali, e tutte e cinque con i costi doppi, con discese un po' piu' piccole: dal 48% al 75%, contro l'86%.
- E' un solo periodo, con due grandi rialzi: nessuno sa se si ripetera'. Questo confronto e' un metro di paragone, non un consiglio di investimento.

### Tutte le prove sul bitcoin

Dalla migliore alla peggiore con i costi normali (euro su un conto da 10.000, puntata fissa).

Regole che comprano e vendono (16):

| Prova | Fonte | Operazioni | Senza costi | Costi normali | Costi doppi | Peggior discesa | Criteri superati |
|---|---|---:|---:|---:|---:|---:|---:|
| K8 Incrocio medie 50/200 + filtro tendenza | jesse + crypto-regime-analyzer | 65 | +65.556 | +60.609 | +55.662 | 7.753 | 3 su 5 |
| K8 Incrocio medie 50/200 | jesse | 115 | +67.030 | +59.260 | +51.489 | 11.218 | 3 su 5 |
| K8 Incrocio medie 50/200 + filtro regime | jesse + regime-detection | 112 | +60.754 | +53.160 | +45.567 | 11.978 | 3 su 5 |
| VolatilitySystem | freqtrade-strategies | 186 | +54.026 | +45.054 | +36.082 | 10.819 | 3 su 5 |
| E1 rottura di 24 ore con trailing | Nucleus (serie E) | 1.559 | +19.347 | +7.849 | -3.649 | 7.756 | 1 su 5 |
| K3 RSI2 di Connors + filtro tendenza | jesse + crypto-regime-analyzer | 513 | +10.937 | +40 | azzerato | tutto il conto | 1 su 5 |
| E2 rottura di 24 ore con uscita a fette | Nucleus (serie E) | 1.147 | +7.821 | -461 | -8.743 | 9.321 | 1 su 5 |
| K3 RSI2 di Connors + filtro regime | jesse + regime-detection | 59 | +232 | -1.025 | -2.283 | 2.545 | 0 su 5 |
| G dollaro BCE | Nucleus (serie G) | 419 | -477 | -1.242 | -2.007 | 2.012 | 1 su 5 |
| H rimbalzo del giorno dopo | Nucleus (serie H) | 323 | -1.940 | -2.838 | -3.736 | 3.886 | 1 su 5 |
| FAdxSmaStrategy | freqtrade-strategies | 174 | +832 | -2.862 | -6.557 | 7.206 | 1 su 5 |
| Controllo della serie E (target 2R) | Nucleus (serie E) | 1.559 | +6.933 | -3.823 | azzerato | tutto il conto | 1 su 5 |
| K3 RSI2 di Connors | jesse | 832 | +11.968 | -5.659 | azzerato | tutto il conto | 1 su 5 |
| F apertura di New York | Nucleus (serie F) | 1.715 | +5.740 | azzerato | azzerato | tutto il conto | 1 su 5 |
| TrendFollowingStrategy | freqtrade-strategies | 329 | -38.851 | azzerato | azzerato | tutto il conto | 1 su 5 |
| C1 candela avvolgente M15 con tendenza H1 | Nucleus (serie C) | 1.341 | -3.285 | azzerato | azzerato | tutto il conto | 1 su 5 |

Regole che solo comprano (31):

| Prova | Fonte | Operazioni | Senza costi | Costi normali | Costi doppi | Peggior discesa | Criteri superati |
|---|---|---:|---:|---:|---:|---:|---:|
| Skill regime-detection: medie 10/30 giornaliere | agiprolabs regime-detection | 31 | +91.853 | +87.359 | +82.864 | 7.458 | 2 su 5 |
| K1 Donchian 20 + media 200 + filtro tendenza | jesse + crypto-regime-analyzer | 57 | +48.450 | +44.786 | +41.122 | 6.016 | 2 su 5 |
| K1 Donchian 20 + media 200 | jesse | 80 | +49.010 | +44.177 | +39.345 | 8.706 | 2 su 5 |
| Uscita: stop a tempo 50 candele | agiprolabs exit-strategies | 429 | +54.882 | +41.612 | +28.341 | 15.186 | 2 su 5 |
| K1 Donchian 20 + media 200 + filtro regime | jesse + regime-detection | 76 | +45.473 | +40.951 | +36.429 | 9.191 | 2 su 5 |
| Uscita: a fette | agiprolabs exit-strategies | 284 | +48.809 | +37.574 | +26.338 | 17.419 | 3 su 5 |
| Uscita: stop fisso 10% | agiprolabs exit-strategies | 283 | +46.708 | +35.478 | +24.249 | 17.260 | 3 su 5 |
| Skill regime-detection: medie 10/30 su H1 | agiprolabs regime-detection | 1.051 | +56.183 | +31.291 | +6.400 | 17.955 | 2 su 5 |
| K2 Rottura di volatilita' (Larry Williams) | pyupbit-autotrade | 973 | +48.564 | +29.101 | +9.638 | 13.673 | 2 su 5 |
| K2b Rottura di volatilita' + media 15 | pyupbit-autotrade | 756 | +43.431 | +28.311 | +13.191 | 7.373 | 2 su 5 |
| K5 SimpleBollinger + filtro tendenza | jesse + crypto-regime-analyzer | 678 | +42.877 | +27.860 | +12.843 | 8.752 | 2 su 5 |
| K2 Rottura di volatilita' (Larry Williams) + filtro regime | pyupbit-autotrade + regime-detection | 851 | +41.772 | +24.750 | +7.728 | 12.729 | 2 su 5 |
| K5 SimpleBollinger | jesse | 1.016 | +47.119 | +24.746 | +2.373 | 15.206 | 2 su 5 |
| K2 Rottura di volatilita' (Larry Williams) + filtro tendenza | pyupbit-autotrade + crypto-regime-analyzer | 629 | +37.186 | +24.606 | +12.026 | 10.254 | 2 su 5 |
| K2b Rottura di volatilita' + media 15 + filtro regime | pyupbit-autotrade + regime-detection | 647 | +35.592 | +22.653 | +9.713 | 6.021 | 2 su 5 |
| K2b Rottura di volatilita' + media 15 + filtro tendenza | pyupbit-autotrade + crypto-regime-analyzer | 520 | +32.976 | +22.577 | +12.178 | 6.216 | 2 su 5 |
| K5 SimpleBollinger + filtro regime | jesse + regime-detection | 888 | +41.998 | +22.428 | +2.858 | 13.804 | 2 su 5 |
| K7 Supertrend + filtro tendenza | freqtrade-strategies + crypto-regime-analyzer | 580 | +34.456 | +20.825 | +7.194 | 6.747 | 3 su 5 |
| Uscita: trailing ATR 2,5 | agiprolabs exit-strategies | 758 | +36.026 | +18.485 | +943 | 15.348 | 2 su 5 |
| Uscita: trailing EMA 20 | agiprolabs exit-strategies | 827 | +34.155 | +15.427 | -3.300 | 19.806 | 1 su 5 |
| K7 Supertrend | freqtrade-strategies | 851 | +35.274 | +15.174 | -4.927 | 13.246 | 1 su 5 |
| Skill regime-detection: adattiva su H1 | agiprolabs regime-detection | 793 | +25.506 | +9.710 | -6.087 | 12.742 | 1 su 5 |
| K7 Supertrend + filtro regime | freqtrade-strategies + regime-detection | 776 | +24.620 | +6.326 | azzerato | tutto il conto | 1 su 5 |
| Candela a martello (solo forma) | tradermonty stockbee | 264 | +5.901 | +4.442 | +2.984 | 1.746 | 3 su 5 |
| Skill regime-detection: adattiva giornaliera | agiprolabs regime-detection | 30 | +4.054 | +1.460 | -1.134 | 10.369 | 0 su 5 |
| K4 BbandRsi + filtro tendenza | freqtrade-strategies + crypto-regime-analyzer | 155 | +6.531 | +1.349 | -3.834 | 12.579 | 1 su 5 |
| K6 TradingView_RSI + filtro regime | jesse + regime-detection | 147 | +3.680 | +326 | -3.027 | 4.621 | 1 su 5 |
| K4 BbandRsi + filtro regime | freqtrade-strategies + regime-detection | 27 | -6.993 | -7.867 | -8.741 | 9.702 | 0 su 5 |
| K4 BbandRsi | freqtrade-strategies | 232 | -1.086 | -8.890 | azzerato | tutto il conto | 1 su 5 |
| K6 TradingView_RSI + filtro tendenza | jesse + crypto-regime-analyzer | 1.111 | -8.488 | azzerato | azzerato | tutto il conto | 1 su 5 |
| K6 TradingView_RSI | jesse | 1.685 | +532 | azzerato | azzerato | tutto il conto | 1 su 5 |

Le prove "Uscita: ..." usano tutte la stessa entrata (rottura del massimo delle 24 ore, solo acquisti) e cambiano solo il modo di uscire; le prove "Skill regime-detection" usano la strategia della skill stessa, solo acquisti.

## Ne vale la pena?

- **EUR/USD: no.** La migliore delle prove con molte operazioni guadagna circa 90 euro l'anno su 10.000 con i costi normali, e perde con i costi doppi. Tutte le altre perdono, tranne TrendFollowingStrategy, che con 10 operazioni in 6 anni non si distingue dalla fortuna.
- **Bitcoin con le regole di Nucleus: no.** Le prove che guadagnano anche con i costi doppi lo fanno con discese tra il 48% e il 95%, tranne la candela a martello (discesa del 16%, +2.984 euro in 7 anni con i costi doppi, solo acquisti). La parte delle vendite perde in 13 prove su 16. E il guadagno delle migliori dipende da poche operazioni in due periodi di forte rialzo.

## Si puo' migliorare?

- **EUR/USD: no.** Prima dei costi le prove sono come una moneta: 16 guadagnano e 16 perdono. Non c'e' niente da far crescere: i ritocchi troverebbero solo combinazioni fortunate nel passato.
- **Bitcoin: non dentro Nucleus.** Mettere meno soldi in ogni operazione abbassa la discesa, ma abbassa piu' o meno nella stessa misura anche il guadagno. Restano due problemi che nessun ritocco risolve: poche operazioni e un guadagno che viene da due soli rialzi. Ogni variante scelta guardando questi risultati sarebbe un nuovo tentativo, con criteri da scrivere prima.

## Lasciar perdere?

- **EUR/USD: si'.**
- **Bitcoin per Nucleus: si'.**
- **Bitcoin come investimento lento, solo in acquisto: gia' provato.** E' la strada di CR1 (Ufficio Cripto, 17/10/2026: bitcoin comprato sopra la media a 200 giorni), bocciata con un calo massimo del 67%. Le cinque regole migliori di oggi, reinvestendo i guadagni (K1 e K8, da sole e con il filtro tendenza, e le medie 10/30 giornaliere), hanno cali dal 48% al 75%: stessa conclusione.

## Cosa fare adesso

1. Considera chiuse le prove su EUR/USD e bitcoin per Nucleus: non c'e' nessun EA da scrivere per questi due mercati.
2. Non riprendere le regole bocciate cambiando i parametri per farle passare: ogni variante e' un nuovo tentativo e rischia di trovare solo una combinazione fortunata.
3. Segui il piano che hai scelto oggi (decisione del 20/10/2026, scritta in `1_Bot/README.md`): nessuna nuova idea di trading fino al 20/01/2027 almeno, e il portafoglio di carta C da novembre 2026.

## Note

- Le prove di robustezza (varianti vicine dei parametri, ultimo terzo del periodo, tick reali) si fanno solo per le idee che superano i criteri: nessuna li ha superati, quindi non sono servite.
- Il programma backtest-expert (repository tradermonty) ha giudicato da scartare (REJECT) o con rischio oltre il limite (RISK_LIMIT_EXCEEDED) tutte le prove che ha potuto valutare.
- Dove gli autori pubblicano i risultati delle loro strategie sul bitcoin, abbiamo controllato che la nostra copia delle regole si comporti in modo simile. Unica eccezione, K6 TradingView_RSI: abbiamo provato la regola scritta nel file (RSI a 5), come registrato prima, mentre il risultato pubblicato dall'autore corrisponde a un RSI a 14. Lo segnalo solo per completezza: provarlo adesso sarebbe una variante scelta dopo aver visto i risultati.
- I costi sono stime prudenti, non quelli esatti del tuo broker.

## Dove trovare i dettagli

- `riepilogo_numeri.csv`: tutti i numeri di questa pagina, una riga per prova.
- `EURUSD/` e `BTC/`: le operazioni di ogni prova (CSV, una riga per operazione) e i risultati in testo (`*_risultati.txt`).
- `codice/`: i programmi in Python. `codice/fonti_fase2.md` dice da quale repository viene ogni regola, con versione e licenza, e da dove vengono i dati.
- `README.md`: che cosa c'e' nella cartella e come rifare i calcoli.
- Regole e criteri, scritti prima delle prove, sono nel Manuale di riferimento Nucleus (capitolo 8).
