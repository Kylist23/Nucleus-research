# Esperimento libero: raddoppiare 10.000 euro sull'oro (14/10/2026)

Fatto senza le regole, le idee e i file di Nucleus. Nessun file di Nucleus modificato: tutto sta in questa cartella.
Dati usati (solo lettura): storico M5 del broker 2016-2022, chiusure Stooq 2015 per calcolare le medie iniziali, cambio euro-dollaro BCE.
Script: `raddoppio_libero.py`.

## In breve
Quasi. La migliore regola scelta in modo onesto porta 10.000 euro a circa 14.500-19.900 euro nel 2016-2022. Il risultato dipende quasi tutto da un numero che non conosco: lo swap degli acquisti di oro del tuo broker. E la regola migliore non e' un sistema furbo: e' comprare l'oro con leva 1,5 e tenerlo. Nessuna regola di entrata e uscita ha fatto meglio.

## Il metodo (scelto prima di guardare i risultati)
1. Ho diviso i dati in due: 2016-2019 per scegliere, 2020-2022 per verificare. Cosi' non si puo' "barare" adattando la regola a dati gia' visti.
2. Cinque candidati, solo acquisti (l'oro nel lungo periodo tende a salire, vendere allo scoperto va contro questa tendenza):
   - compra e tieni;
   - tendenza a 50, 100 o 200 giorni: comprati sopra la media, fuori sotto;
   - "compra il ribasso" (RSI a 2 giorni sotto 10 in un mercato sopra la media a 200 giorni).
3. Cinque livelli di leva: 1; 1,5; 2; 2,5; 3. La leva vuol dire muovere piu' soldi di quelli che hai: con leva 1,5, 10.000 euro si muovono come 15.000.
4. Regola di scelta: il rendimento piu' alto nel 2016-2019 con una perdita massima dal picco non oltre il 30%. Sopra il 30% una persona normale, di solito, chiude tutto nel momento peggiore.
5. Costi realistici: spread reale del broker e swap degli acquisti (il costo per tenere aperta la posizione di notte).

## Risultati
Scelta sul 2016-2019: compra e tieni con leva 1,5. Le regole di tendenza e il "compra il ribasso" hanno reso meno a parita' di leva.

| Swap annuo degli acquisti (ipotesi) | 2020-2022 (verifica) | 2016-2022 (10.000 euro diventano) | Perdita massima dal picco |
|---|---|---|---|
| 0% (nessuno swap) | x1,23 | 19.921 euro | -33% |
| 1,2% (come lo swap reale delle vendite) | x1,17 | 17.569 euro | -35% |
| 3% (stima prudente) | x1,08 | 14.547 euro | -39% |

Per anno, con swap 1,2%: 2016 +7%, 2017 +15%, 2018 -4%, 2019 +25%, 2020 +35%, 2021 -9%, 2022 -3%.

## Cosa ho imparato
1. Sull'oro 2016-2022 nessuna regola di entrata e uscita ha battuto il semplice "compra e tieni". Entrare e uscire ha solo aggiunto costi e falsi segnali.
2. Raddoppiare dipende dalla leva, non da un'abilita'. La leva ha funzionato perche' l'oro e' salito del 71%. Con un oro in calo la stessa leva avrebbe fatto perdere molto di piu'.
3. Il prezzo del raddoppio e' una perdita temporanea del 33-39%: a un certo punto il conto avrebbe perso oltre un terzo del suo valore massimo prima di risalire.
4. Per tenere l'oro a lungo, un CFD con swap non e' lo strumento adatto: lo swap si mangia una parte grande del guadagno. Un prodotto che detiene oro fisico (ETC) non paga swap, ma non ha leva: senza leva e senza costi l'oro rendeva x1,64 (Da verificare: costi annui di un ETC).
5. Il passato non dice nulla di certo sul futuro: questo test spiega cosa avrebbe funzionato, non cosa funzionera'.

## Cosa puoi verificare tu, senza cambiare nulla
Lo swap reale degli acquisti di oro: in MetaTrader 5, finestra Market Watch (Osservazione mercato), tasto destro su XAUUSD, poi "Specification" (Specifiche). Alla voce "Swap long" vedi il valore. E' il numero che decide tra 14.500 e 19.900 euro.

## Aggiornamento con lo swap reale (14/10/2026, 17:50 UTC)
L'autore ha letto in MetaTrader 5: Swap long = -12,6. Ho supposto che sia in punti, cioe' 12,6 $ per lotto (100 once) a notte (Da verificare: voce "Tipo di swap" nelle Specifiche). Ai prezzi 2016-2022 vale circa il 2,5-4,3% l'anno del valore.

Rifatto lo stesso metodo, senza altri cambi (`raddoppio_libero.py ... 12.6pt`):
- Scelta sul 2016-2019: tendenza a 50 giorni con leva 2 (x1,23, perdita massima -27,8%). Il compra e tieni con leva 1,5 ora supera di poco il limite del 30% (-30,8%).
- Verifica 2020-2022: x1,17, perdita massima -36,2%.
- Periodo intero: 10.000 euro diventano 14.643 euro (x1,46), perdita massima -36,2%, 61 entrate.
- Per anno: 2016 +18%, 2017 +1%, 2018 -7%, 2019 +12%, 2020 +15%, 2021 -11%, 2022 +17%.

Conclusione: con lo swap reale il raddoppio non c'e'. Lo swap costa circa il 7% l'anno del capitale con leva 2.
Limite: il tester applica lo swap di oggi a tutto il passato; nel 2016-2021 i tassi erano piu' bassi e lo swap probabilmente anche (Da verificare).
