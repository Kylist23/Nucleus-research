# Fase 1 — Fondazione Dati: chiusura

Data: 23 settembre 2026. Branch: `fase-1-chiusura`.

## Cosa è stato fatto

- Il codice di acquisizione (ECB e H.10) ora segue le Regole dei dati di `CLAUDE.md`: nome
  file unico e scrittura esclusiva (mai sovrascrittura), ogni tentativo registrato in
  `data/logs/acquisition_attempts.jsonl` anche quando fallisce, SHA-256 nei metadati.
- I report di qualità e il report cross-source sono stati spostati da `data/raw/` a
  `data/reports/`. `data/raw/` contiene ora solo originali e metadati.
- I test importano le funzioni da `src/` (hash, parsing H.10) invece di reimplementarle.
  Aggiunti test per: rifiuto della sovrascrittura, registrazione di un download fallito
  simulato (senza rete), corrispondenza SHA-256.
- Il parsing dell'H.10 usa un'unica funzione condivisa (`src/h10_parsing.py`) che cerca
  l'intestazione per contenuto ("Time Period") e la colonna EUR per nome esatto, non più
  `skiprows=5` fisso né una sottostringa "EU" nel nome colonna.
- `docs/NOTE_FONTI.md` spiega la differenza tra i due fixing e classifica le date presenti
  in una sola fonte.
- `data/processed/eur_usd_daily.parquet`: le due serie unite per data, valori mancanti come
  vuoti. Un test verifica che ricostruendolo il risultato sia identico.

## Confronto con i criteri del Blueprint §13

| Criterio (dal Blueprint) | Si applica? | Nota |
|---|---|---|
| Rieseguendo la pipeline, i dati risultanti sono identici al bit | Solo in parte | Vale per la costruzione del Parquet (`tests/test_processed_data.py::test_build_is_reproducible`). Non vale per un nuovo download: una fonte viva può aver pubblicato osservazioni nuove nel frattempo — non è un difetto della pipeline. |
| Ogni gap è spiegato (fine settimana, festività) o segnalato | Sì | `docs/NOTE_FONTI.md`. 47 date spiegate da festività TARGET2, 246 da festività federali USA, 5 dal ritardo di pubblicazione dell'H.10, 6 da chiusure straordinarie probabili (non verificate), 3 restano senza spiegazione — dichiarate come tali. |
| Dieci barre scelte a caso coincidono con una fonte indipendente | Non applicabile alla lettera | Non abbiamo barre OHLC né una terza fonte. Usiamo però due fonti ufficiali indipendenti (ECB, Federal Reserve) confrontate su tutte le date in comune, non solo dieci a caso (`data/reports/cross_source/`). |
| Tutti i timestamp sono in UTC, verificato anche sul cambio d'ora legale | Non applicabile alla lettera | Le osservazioni hanno solo una data di calendario, non un orario: non c'è un timestamp da verificare contro l'ora legale. I timestamp di acquisizione (`retrieved_at`) sono già in UTC. |
| I test automatici passano | Sì | 31 test, `pytest -q` verde (vedi sotto). |
| Sai spiegare a parole tue cosa fa ogni file che abbiamo creato | Sì | Riassunto in fondo a questo documento. |

Nota anche sulla coerenza OHLC richiesta altrove nel §13 ("massimo ≥ apertura, chiusura,
minimo"): non applicabile. ECB e H.10 sono tassi di riferimento giornalieri singoli
(fixing), non barre OHLC — quel controllo presuppone dati come quelli di Dukascopy, non
usati qui.

## Cosa resta aperto

- Non è stato eseguito alcun nuovo download in questa sessione: gli script aggiornati non
  sono stati ancora provati contro le fonti reali (serve un'autorizzazione esplicita).
- Esiste una sola acquisizione valida per fonte (quelle del 20 settembre 2026, precedenti
  alle nuove regole per l'ECB — vedi `data/raw/ecb/PRE_RULES_NOTE.md`).
- 3 date (2019-01-14, 2019-02-20, 2020-11-27) restano senza spiegazione in
  `docs/NOTE_FONTI.md`.
- La classificazione delle festività usa un calcolo proprio (algoritmo di Gauss per la
  Pasqua, regole standard USA), non una libreria dedicata né una fonte ufficiale scaricata:
  un errore nella formula darebbe una classificazione sbagliata.

## Test

```
.venv/bin/python -m pytest -q
```
31 test, tutti superati.

## Riassunto di ogni file (nuovo o modificato)

- `src/hashing.py` — calcola l'impronta SHA-256 di un file.
- `src/exclusive_write.py` — scrive un file solo se non esiste già; altrimenti si ferma.
- `src/attempt_log.py` — aggiunge una riga a `data/logs/acquisition_attempts.jsonl` per
  ogni tentativo di download, riuscito o no.
- `src/h10_parsing.py` — legge il CSV H.10 cercando l'intestazione e la colonna EUR per
  nome, non per posizione fissa.
- `src/acquire_ecb.py` — scarica lo storico ECB, nome file unico, registra il tentativo.
- `src/acquire_h10.py` — come sopra, per l'H.10 (già faceva il nome unico; ora anche
  scrittura esclusiva e registro tentativi).
- `src/quality_ecb.py`, `src/quality_h10.py` — controlli di qualità sui dati scaricati;
  scrivono il report in `data/reports/`.
- `src/validate_cross_source.py` — confronta ECB e H.10 sulle date in comune; scrive il
  report in `data/reports/cross_source/`.
- `src/build_processed.py` — unisce ECB e H.10 in un'unica tabella per data, salvata in
  `data/processed/eur_usd_daily.parquet`.
- `tests/test_ecb.py`, `tests/test_h10.py`, `tests/test_cross_source.py` — verificano i
  dati scaricati e i report, ora usando le funzioni di `src/`.
- `tests/test_acquisition_rules.py` — verifica le regole di scrittura esclusiva e di
  registrazione dei tentativi falliti.
- `tests/test_processed_data.py` — verifica la tabella unita e la sua riproducibilità.
- `docs/NOTE_FONTI.md` — spiega le differenze tra ECB e H.10.
- `data/raw/ecb/PRE_RULES_NOTE.md` — spiega perché il file ECB esistente non segue ancora
  lo schema a nome unico.
