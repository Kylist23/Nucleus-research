# Report: provare a raddoppiare 10.000 euro sull'oro (14/10/2026)

## In breve
Non ci sono riuscito. Con le regole di Nucleus (costi e swap pagati due volte) l'EA trasforma 10.000 euro in 6.810 euro nel 2016-2022 e si ferma nel 2017 per lo stop di emergenza al 40%. Anche senza nessun costo finisce a 9.808 euro. L'unico modo di raddoppiare sarebbe stato comprare l'oro con leva 2 e tenerlo: pero' lo si sa solo col senno di poi, e con costi realistici non basta.

## Cosa ho fatto
1. Ho scritto la regola e i criteri nel Manuale prima di guardare i risultati (Serie D, tentativo 1, 14/10/2026).
2. Regola: ogni giorno, se l'oro chiude sopra la media degli ultimi 200 giorni si sta comprati, se chiude sotto si sta venduti. La dimensione della posizione segue la volatilita' (quanto si muove l'oro): obiettivo 25% l'anno, leva massima 3. La leva e' la scelta che rende il raddoppio possibile: senza leva, con l'oro a +71% nel periodo, non si raddoppia.
3. Ho simulato la regola in Python sui tuoi dati del broker (`Dati/XAUUSD_M5_2016-2022.csv`), con il cambio euro-dollaro della BCE e le chiusure Stooq del 2015 solo per calcolare la media iniziale. Script: `Scrematura_Python/sim_d1_raddoppio.py`.
4. Ho scritto l'EA `NucleusEA_D1.mq5` (blocco dei conti reali attivo) e l'ho copiato sul Mac in `~/Nucleus/mt5/Experts/`. Serve a misurare lo swap reale, che in Python e' solo stimato.

## Risultati (simulazione Python, Verificato con lo script)

| Strategia | Costi | Capitale finale | Perdita massima dal picco |
|---|---|---|---|
| Tendenza 200 giorni (l'EA) | doppi (regola Nucleus) | 6.810 euro | -40% (stop di emergenza nel 2017) |
| Tendenza 200 giorni | normali | 6.908 euro | -41% |
| Tendenza 200 giorni | nessuno | 9.808 euro | -40% |
| Comprare e tenere, senza leva | doppi / normali / nessuno | 9.238 / 13.636 / 16.442 euro | -40% / -31% / -22% |
| Comprare e tenere, leva 2 | doppi / normali / nessuno | 8.614 / 14.253 / 22.884 euro | -41% / -41% / -30% |

Tendenza 200 giorni, costi doppi: 12 operazioni, acquisti -900 euro, vendite -2.290 euro.

## Perche' non funziona
- Falsi segnali: nel 2016-2017 l'oro ha attraversato spesso la media a 200 giorni, e con la leva ogni errore costava caro (-35% nel 2017).
- Lo swap (il costo per tenere aperta una posizione di notte): tenere l'oro per 7 anni con leva costa molto. Per le vendite lo swap reale del broker e' circa l'1,2% l'anno del valore (Verificato: test B2 v1.00, 345 notti). Per gli acquisti ho stimato il 3% (Da verificare: lo dira' il test MT5).
- Raddoppiare e' una questione di rischio, non di abilita': con leva 2 si raddoppiava solo perche' l'oro e' salito del 71%. Se fosse sceso del 35%, la stessa scelta avrebbe dimezzato il capitale.

## Criteri Nucleus
Bocciati: operazioni 12 (servono 100), risultato con costi doppi negativo, acquisti e vendite negativi, drawdown 40% (limite 10%). L'obiettivo di 20.000 euro non e' raggiunto.

## Cosa resta da fare
- Test MT5 di conferma (passi nel messaggio del thread): dira' lo swap reale degli acquisti.
- Sul Mac l'EA non e' ancora registrato in git.
