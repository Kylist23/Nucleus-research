# Note sulle differenze tra ECB e H.10

Confronto tra le due fonti usate da Nucleus per EUR/USD: la Banca Centrale Europea (ECB) e
l'H.10 della Federal Reserve. Riguarda solo l'unica acquisizione oggi disponibile per
ciascuna fonte (i file in `data/raw/ecb/` e `data/raw/h10/`).

## Perché i due tassi non sono mai identici

La BCE fissa il cambio EUR/USD alle 14:15 CET (l'orario è scritto dentro lo stesso file
CSV, colonna `TITLE_COMPL`). L'H.10 riporta invece il "noon buying rate" di New York, cioè
il tasso di riferimento di mezzogiorno, ora di New York — diverse ore prima o dopo, a
seconda della stagione (differenza di fuso tra Francoforte e New York: 6 ore d'inverno,
5 in estate).

Un mercato come EUR/USD si muove in modo continuo durante il giorno. Poche ore di
differenza tra le due rilevazioni sono una **spiegazione plausibile** della differenza
media assoluta osservata tra le due serie: **0,00299** (circa 3 millesimi di dollaro),
calcolata su 6.854 date in comune. Non è una prova: per dimostrarlo servirebbero dati
infragiornalieri, che Nucleus non ha.

## Date presenti in una sola fonte

Ho ricalcolato le date presenti in una fonte e assenti nell'altra, e le ho confrontate con
due calendari di festività calcolati direttamente (algoritmo di Gauss per la Pasqua, regole
standard per le festività USA — nessuna libreria nuova installata).

### Presenti solo in H.10, assenti in ECB: 47 date

Tutte e 47 corrispondono a giorni di chiusura TARGET2 (il sistema di pagamenti europeo),
nei quali la BCE non pubblica un tasso:

| Festività              | Date |
|---|---|
| Venerdì Santo          | 14 |
| Lunedì dell'Angelo     | 14 |
| Festa del lavoro (1° maggio) | 11 |
| Santo Stefano (26 dicembre)  | 8 |

Capodanno e Natale non compaiono in questo elenco perché in quei due giorni **entrambe**
le fonti sono chiuse: la data manca da tutte e due le serie, non solo da una.

### Presenti solo in ECB, assenti in H.10: 260 date

- **246** corrispondono a una festività federale statunitense (regola "osservata": se cade
  di sabato si sposta a venerdì, se di domenica a lunedì; il Juneteenth è federale solo dal
  2021):

  | Festività | Date |
  |---|---|
  | Washington's Birthday (Presidents' Day) | 28 |
  | Martin Luther King Jr. Day | 28 |
  | Memorial Day | 28 |
  | Independence Day | 27 |
  | Labor Day | 27 |
  | Columbus Day | 26 |
  | Thanksgiving | 26 |
  | Veterans Day | 25 |
  | Capodanno (USA) | 14 |
  | Christmas (USA) | 12 |
  | Juneteenth | 5 |

- **5** sono oltre l'ultima data pubblicata dall'H.10 in questa acquisizione
  (2026-09-11): 2026-09-14, 15, 16, 17, 18. Non sono festività: l'H.10 non ha ancora
  pubblicato quei giorni al momento del download (differenza già nota tra la fine
  richiesta, 2026-09-18, e l'ultima osservazione ricevuta).

- **6** corrispondono a chiusure straordinarie note, non calcolabili con un calendario
  fisso — riportate come **probabili**, non verificate con la fonte primaria in questa
  sessione (nessun accesso a internet):
  - 2001-09-11 — giorno degli attentati, mercati statunitensi chiusi.
  - 2017-01-20 e 2021-01-20 — giorno dell'insediamento presidenziale, festivo federale
    per gli uffici dell'area di Washington D.C. ogni quattro anni.
  - 2018-12-05 — giorno di lutto nazionale per la morte del presidente George H. W. Bush.
  - 2018-12-24 e 2020-12-24 — vigilia di Natale, chiusura degli uffici federali disposta
    per decreto in alcuni anni (non la stessa ogni anno).

- **9 restano senza spiegazione**: 2001-09-11, 2017-01-20, 2018-12-05, 2018-12-24,
  2019-01-14, 2019-02-20, 2020-11-27, 2020-12-24, 2021-01-20 — le prime 6 di queste 9
  sono anche le "probabili" appena elencate; le riporto qui perché il calendario fisso da
  solo non le spiega, e non ho potuto verificarle contro la fonte originale.

  Le tre che restano **davvero senza alcuna spiegazione, nemmeno probabile**, sono:
  **2019-01-14, 2019-02-20, 2020-11-27**. Non corrispondono a nessuna festività nota,
  fissa o straordinaria, che ho trovato. Possono essere un giorno in cui l'H.10 non è
  stato pubblicato per un motivo tecnico della fonte, ma non lo so con certezza.

## Limiti di questa nota

- I calendari (TARGET2 e festività USA) sono calcolati con formule note, non presi da una
  fonte ufficiale scaricata: un errore nella formula produrrebbe classificazioni sbagliate.
- Non ho avuto accesso a internet in questa sessione: le chiusure straordinarie sopra sono
  ricordate, non verificate su una fonte primaria.
- Il confronto riguarda una sola acquisizione per fonte. Una fonte che rivede i propri dati
  nel tempo (entrambe lo fanno, vedi `sources/ecb.yaml` e `sources/h10.yaml`) potrebbe dare
  risultati diversi in futuro.
