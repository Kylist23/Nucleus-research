# Serie CR (Ufficio Cripto): proposta (bozza 17/10/2026, da approvare)

Skill usata: nucleus-test-ea, punto 0 (revisione scettica) e bozza del punto 1 (criteri).
Nessun dato di risultato e' stato calcolato: ho controllato solo la qualita' del file.

## L'idea in 3 righe (CR1, consigliata)
- Entra: il venerdi', se la chiusura del Bitcoin e' sopra la sua media degli ultimi 200 giorni di borsa, si tiene Bitcoin.
- Esce: il venerdi', se la chiusura e' sotto la media, si passa in liquidita'.
- Rischia: tutta la quota cripto e' investita o ferma; nessuna leva, nessuna vendita allo scoperto.

## Perche' dovrebbe guadagnare (onesto)
Il Bitcoin non paga interessi ne' dividendi: il guadagno viene solo da chi compra dopo a un prezzo piu' alto.
La regola non crea guadagno; prova solo a evitare parte dei crolli (-70/-85% gia' successi piu' volte).
Seguire il trend ha gia' fallito 3 volte su oro e indici in Nucleus (A2, A3, D1). Fallisce nei mercati laterali (entra ed esce in perdita).

## Problemi trovati
| Problema | Gravita' | Rimedio |
|---|---|---|
| Poche operazioni: con questa regola ci si aspettano decine di cambi, non 100 | Grave | Trattarla come un portafoglio (come la strada 1), non come un EA. Il test puo' solo dire se riduce i crolli, non provare un vantaggio. |
| Dati Stooq solo dal lunedi' al venerdi' (4.202 righe, 1_Bot/Dati/Stooq_manuale_2026-10-13/btcusd_d.csv) | Minore | Decidere solo il venerdi'; il prezzo d'esecuzione e' la chiusura del lunedi' successivo (mai lo stesso venerdi'). |
| 2010-2013: mercati piccoli e prezzi dubbi | Grave | Usare solo dal 2014-01-01. |
| Un solo mercato che e' salito moltissimo: quasi tutto sembra buono sul Bitcoin | Grave | Confronto obbligatorio con "compra e tieni" e con l'acquisto mensile fisso (PAC). |
| Conosco gia' a grandi linee la storia del Bitcoin | Minore | Le soglie le scrivo prima e le dichiaro; la cassaforte 2023-oggi resta intatta. |
| Costi: commissioni 0,1-1,5% a seconda dell'app, tasse 33% (Da verificare) | Grave | Costo 0,5% per lato, pagato due volte (1% per lato). |

## Criteri proposti (scritti prima, da registrare nel Manuale dopo il tuo si')
- Periodo: 2014-01-01 / 2022-12-31. Cassaforte 2023-01-01 / oggi intatta.
- Costo 1% per ogni acquisto e ogni vendita (0,5% raddoppiato).
- Risultato finale positivo e sopra la liquidita'.
- 2014-2018 e 2019-2022 entrambi positivi.
- Calo massimo dal picco non oltre il 50% (il "compra e tieni" ha fatto molto peggio).
- Calo massimo almeno 20 punti migliore di "compra e tieni".
- Basta un criterio non superato e l'idea e' bocciata. Massimo 3 tentativi nella Serie CR.

## Metro di confronto (non e' un tentativo)
- Compra e tieni dal 2014.
- Acquisto fisso ogni mese (PAC), senza regole.

## Escluso
- La quota del 5% di Bitcoin dentro il portafoglio C: L'autore ha deciso che le cripto sono una strada separata (17/10/2026).

## Dopo il test
Se CR1 passa: portafoglio di carta da 2026-11, separato da quello della strada 1, per almeno 3 mesi.
Il passaggio a soldi veri (anche piccoli) lo decidi e lo fai solo tu, a mano, dopo la prova.
