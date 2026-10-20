# Proposta Serie C, tentativo 1: piccoli guadagni leggendo le candele (XAUUSD)

Data: 14/10/2026. Stato: approvata dall'autore il 14/10/2026; BOCCIATA nella scrematura in Python lo stesso giorno (screen_c1.py: 1.379 operazioni, -221,8 R con costi doppi). EA non scritto.
Procedura: skill nucleus-test-ea, punto 0 (revisione scettica).

## 1. I costi contro i target piccoli (Verificato)

Fonte: `1_Bot/Dati/XAUUSD_M5_2016-2022.csv`, calcolo `1_Bot/Scrematura_Python/costi_scalping.py`.
Commissioni del broker nel tester: 0 (`Risultati_test/B2_v1.01_TESTER_XAUUSD.csv`, colonna commission, somma 0 su 1.934 righe). Il costo e' quindi lo spread.

- Spread mediano 0,18 $ (90 percentile 0,32 $). Range mediano di una candela M5: 0,76 $.
- Spread pagato due volte (regola del progetto): 0,36 $ per operazione.

| Target = stop | Costo 2x in % del target | Operazioni vinte necessarie solo per pareggiare |
|---|---|---|
| 0,5 $ | 72% | 86% |
| 1 $ | 36% | 68% |
| 2 $ | 18% | 59% |
| 3 $ | 12% | 56% |
| 5 $ | 7% | 54% |

Una regola senza vantaggio vince circa il 50%. Con target da 0,5-1 $ servirebbe vincere 68-86 volte su 100: nessuna regola sulle candele ci arriva in modo credibile. Conclusione: i target piccolissimi sono bocciati prima di iniziare.

Ore migliori: 15:00-18:59 server (14-18 in Italia), dove il costo doppio e' il 23-33% del range di una candela M5; peggiori 01:00-07:59 (70-92%).

## 2. Regola proposta (3 righe)

- Entrata: grafico M15, solo tra le 15:00 e le 18:59 server. Se il prezzo H1 e' sopra la media mobile esponenziale a 50 periodi, solo acquisti; sotto, solo vendite. Segnale: candela "avvolgente" (engulfing: il corpo della candela appena chiusa copre tutto il corpo della precedente, di colore opposto) nella direzione del trend. Si entra all'apertura della candela successiva.
- Uscita: stop oltre il minimo (acquisti) o il massimo (vendite) della candela avvolgente; target a 1R (stessa distanza dello stop). Se stop sotto 1,5 $ o sopra 6 $ niente operazione. Chiusura forzata alle 21:30 server: mai posizioni di notte, niente swap.
- Rischio: 0,5% del conto per operazione, una sola posizione alla volta, blocco conti reali attivo.

"Piccoli guadagni" qui significa piccoli in euro per operazione (0,5% di rischio), non piccoli in prezzo.

## 3. Obiezioni (con gravita' e rimedio)

| Problema | Gravita' | Rimedio |
|---|---|---|
| Motivo economico debole: le figure di candela non hanno prove solide di vantaggio. L'unica ragione plausibile e' che nelle ore di Londra e New York i movimenti tendono a proseguire. | Grave | Scrematura in Python prima dell'EA; se non passa, si ferma qui. |
| Tester in "1 minute OHLC": stop e target a pochi dollari vengono eseguiti al prezzo esatto, risultati troppo ottimisti. | Grave | Prova obbligatoria con "Every tick based on real ticks". Da verificare: se il broker ha i tick reali dal 2016. |
| Spread nei dati M5 2021-2022 mediano 0,05 $, molto piu' basso degli anni prima: probabilmente e' lo spread minimo della candela, non quello pagato davvero. | Grave | Nella scrematura uso lo spread del 2016-2019 (circa 0,20 $) come minimo. Da verificare. |
| Parametri: 5 (orari, EMA 50, 1R, stop minimo e massimo). | Minore | Fissi come #define; varianti vicine solo come prova di robustezza. |
| Tentativi: sarebbe la 9a idea provata. Piu' idee si provano, piu' e' facile trovarne una buona per caso. | Grave | Criteri e soglie scritti nel Manuale prima; massimo 3 tentativi nella Serie C. |

## 4. Se approvata, i passi

1. Scrivo i criteri nel Manuale (capitolo 8), prima di guardare qualsiasi risultato.
2. Scrematura in Python sullo storico M5 2016-2022, costi pagati due volte.
3. Solo se passa: EA partendo da NucleusEA_B2, sul branch separato, poi test nello Strategy Tester.
