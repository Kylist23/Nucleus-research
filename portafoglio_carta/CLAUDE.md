# NUCLEUS — Regole per Claude Code

## Cos'è Nucleus
Laboratorio personale di ricerca finanziaria su macOS. Parte da EUR/USD giornaliero.
Principio: controllo e verificabilità prima di autonomia e profitto.
Piano generale: `docs/Blueprint.html`, sezioni 1–13 (le 15 fasi sono in §12).

## Chi è l'utente
L'autore è un principiante di programmazione, finanza e AI.
- Spiega sempre in italiano semplice, senza gergo non spiegato.
- A fine sessione: un riassunto breve di cosa fa ogni file creato o modificato.
- Il codice e i nomi dei file restano in inglese.

## Stato del progetto
- Direzione (decisa il 10/10/2026): strada 1, investimento di lungo periodo con
  diversificazione e ribilanciamento. La Serie A e B di EA sull'oro resta come ricerca.
- Fase 0 (ambiente): completata.
- Fase 1 (fondazione dati): in chiusura.
- Le Decisioni 1 e 2 del Blueprint (§14) sono ARCHIVIATE. Non vanno implementate
  articolo per articolo e non vanno estese. Al loro posto valgono le Regole dei dati qui sotto.
- Il Global Problem & Risk Audit (47 voci) è archiviato. Si consulta solo se serve.

## Regole dei dati
1. Un file scaricato non viene mai sovrascritto né modificato. Ogni download ha un nome unico
   (sorgente + data/ora UTC + identificativo casuale), creato in modo esclusivo.
2. Ogni tentativo di download viene registrato, anche se fallisce: quando (UTC), fonte, URL,
   versione dello script, esito, codice HTTP, dimensione, motivo dell'eventuale errore.
3. Ogni file salvato ha la sua impronta SHA-256 registrata nei metadati.
4. `data/raw/` contiene solo i file originali e i loro metadati. Report e dati elaborati
   vanno in cartelle separate (`data/reports/`, `data/processed/`).
5. Un download fallito, parziale o sospetto non viene mai usato per i calcoli.
6. Tutti gli orari registrati sono in UTC.

## Regole di sicurezza
- Mai cancellare o modificare file in `data/raw/`. Mai `rm -rf`, mai `git push --force`,
  mai riscrivere la storia di Git.
- Non installare pacchetti e non accedere a internet senza chiedere prima.
  Uniche fonti ammesse per ora: API della BCE, Federal Reserve H.10 e, per la strada 1
  (prezzi mensili di indici, ETF, oro e Bitcoin), Stooq (stooq.com), approvato dall'autore il 10/10/2026.
- Nessuna password, chiave o credenziale nel codice o nei file.
- Nessun codice per LLM e nessun codice che operi su un conto reale.
- Eccezione (decisa dall'autore il 10/10/2026): gli EA per MetaTrader 5 in `mt5/` sono ammessi,
  ma solo per lo Strategy Tester e per il conto demo. Ogni EA blocca i conti reali
  (`InpAllowRealAccount=false`) e quel blocco non si toglie mai. Il passaggio a un conto
  reale lo decidiamo insieme più avanti e lo fa solo l'autore, a mano.

## Modo di lavorare
- Prima di cambiamenti grandi: proponi un piano e aspetta l'approvazione.
- Lavora su un branch dedicato, con commit piccoli e messaggi chiari.
- Esegui i test prima di ogni commit: `.venv/bin/python -m pytest -q`
- I test devono importare e verificare il codice in `src/`, non solo i file salvati.
- Preferisci la soluzione più semplice che funziona. Niente documenti formali
  o nuove "decisioni": una nota breve in `docs/` basta.
- Se qualcosa non è chiaro o sembra rischioso, fermati e chiedi.

## Quando una fase è finita
- I criteri di verifica della fase nel Blueprint (§12 e §13) sono soddisfatti,
  oppure è scritto perché non si applicano.
- Tutti i test passano.
- Esiste una nota di chiusura breve in `docs/` (cosa è stato fatto, cosa resta aperto).
- L'autore sa spiegare a parole sue cosa fa ogni file.

Rigore massimo, con revisione esterna, solo per la Fase 4 (backtest), la Fase 7 (Critic)
e qualsiasi cosa tocchi denaro reale.
