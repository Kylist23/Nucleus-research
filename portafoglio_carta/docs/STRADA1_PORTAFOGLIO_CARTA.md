# Strada 1: portafoglio di carta C

Regole approvate dall'autore il 14/10/2026, scritte prima di qualsiasi dato del periodo di prova.
Non si cambiano strada facendo.

## Cosa è
Seguiamo il portafoglio C ogni mese, da novembre 2026 in avanti, con prezzi veri e 10.000 euro finti.
È una prova sul futuro: nessuno ha visto questi dati, quindi non possiamo adattarci a loro.
Non è un tentativo della serie (non cambia pesi né regole) e non apre la cassaforte.
Nessun denaro vero, nessun ordine, nessun conto collegato.

## Regole uguali al test (`STRADA1_SPEC_TEST.md`)
- Pesi §4: 17,5% S&P 500, 7,5% Euro Stoxx 50, 25% obbligazioni, 25% oro, 25% liquidità.
- Costi, bollo, tasse e ribilanciamento di dicembre come §6. Rendimenti come §3 (medie mensili).
- Accanto a C si segue LIQ (100% liquidità) come metro di confronto.
- Versione con i soli prezzi. I dividendi stimati non si usano.

## Cosa cambia
- Mese d'acquisto: 2026-11. Il primo rendimento è quello di 2026-12.
- I mesi da 2023-01 a 2026-10 non vengono mai letti: il codice (`src/path1_paper.py`)
  rifiuta qualsiasi tabella con un mese prima di 2026-11.
- Il valore di dicembre è mostrato prima del ribilanciamento; il mese dopo il calcolo
  lo include (in pratica: piccola differenza dovuta a tasse e costi della vendita).

## Dati
- Solo fonti già ammesse: BCE per S&P 500, Euro Stoxx 50, tasso a 10 anni, Euribor 3 mesi e
  cambio; Stooq per l'oro, scaricato a mano dall'autore (il sito blocca i download automatici).
- Regole dei dati di `CLAUDE.md`: nome unico, SHA-256, registro di ogni tentativo.
- Un mese si chiude solo quando è finito: la media di dicembre si calcola a gennaio.
  Il codice rifiuta il mese in corso e i mesi futuri (in UTC).

## Ogni mese (dal 5 del mese in poi)
1. L'autore scarica l'oro da Stooq in Safari (file `xauusd_d.csv` in Download). Prima cancella il file
   del mese prima, altrimenti Safari salva `xauusd_d-2.csv` e il programma lo rifiuta.
2. Doppio clic su `scripts/Aggiornamento mensile portafoglio.command` (oppure lo fa Claude sul Mac con
   `.venv/bin/python -m src.paper_monthly ~/Downloads/xauusd_d.csv`). Il programma:
   - scarica dalla BCE le 5 serie mensili con `startPeriod=2026-11`: i file nuovi non contengono
     nessun mese della cassaforte;
   - importa l'oro in `data/raw/stooq/` (copia identica, SHA-256, registro);
   - ricostruisce `data/processed/paper_c_monthly.csv` (`src/build_paper_monthly.py`): tiene solo i mesi
     da 2026-11 al mese prima di quello in corso, subito dopo la lettura; la tabella finisce all'ultimo
     mese in cui ci sono tutte le serie; un buco ferma tutto;
   - rigenera e apre la pagina.
3. Se compare un errore, niente cambia nella tabella: si copia il messaggio a Claude.
4. Variazioni grandi rispetto al mese prima (soglie del test) sono scritte in
   `data/reports/paper/quality_paper_monthly.json`: si guardano, non fermano niente.

Calendario: a inizio dicembre 2026 si registra solo l'acquisto (valore 10.000 euro); a inizio gennaio
2027 il primo rendimento (dicembre); a fine 2027 i primi 12 mesi; a fine 2029 i 36 mesi.

## Cosa misuriamo, ogni mese
- Valore di C e di LIQ; rendimento del mese; rendimento da inizio prova; calo dal massimo;
  valore netto se si vendesse tutto oggi (tasse e costo inclusi).

## Quando si giudica
- Prima di 12 mesi di rendimenti: nessun giudizio. Un anno da solo dice pochissimo.
- Allarme: se C scende più del 15% sotto il suo massimo, ne parliamo. Non si cambia il
  portafoglio per questo.
- Dopo 36 mesi: confronto con i criteri del test §7: calo massimo al massimo 25%, nessun anno
  solare sotto -20%, rendimento annuo netto sopra quello di LIQ.
  Contano solo gli anni solari completi, da dicembre a dicembre (2027, 2028, ...): il 2026
  della prova ha un solo mese e non conta come anno (precisazione approvata dall'autore il
  14/10/2026, prima di qualsiasi dato della prova).
- Il verdetto più alto è "C regge sul futuro". Il passaggio al denaro vero lo decide solo l'autore.

## Cosa non dice
- Se C è meglio di D: resta aperto e serve il tentativo 2 con i dividendi veri.

## Pagina da guardare
- `src/paper_dashboard.py` scrive `paper/index.html` (non va su Git, si rigenera): una pagina locale
  con valore, rendimenti, grafico di C contro la liquidità, calo dal massimo, giudizio, composizione
  per attività e storia del test 2001-2022. Nessun collegamento esterno, nessun dato inviato.
- Dati della prova: `data/processed/paper_c_monthly.csv` (da creare con i primi dati).
- `scripts/Portafoglio di carta.command`: con un doppio clic aggiorna la pagina e la apre.
  Sulla Scrivania si mette un alias di questo file.
