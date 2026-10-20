# 1. Bot (EA per MetaTrader 5)

## Stato delle serie di ricerca

| Serie | Tentativo | File | Idea | Esito |
|---|---|---|---|---|
| A | 1 | `EA/Serie_A/NucleusEA_v1_1_A1.mq5` | Incrocio di medie su H1, XAUUSD 2018-2022 | Bocciato: -505 euro, fattore di profitto 0,84 |
| A | 2 | `EA/Serie_A/NucleusEA_v2_A2.mq5` | Rottura dei 20 giorni su D1, 5 mercati | Bocciato: -21 R su 210 operazioni |
| A | 3 | `EA/Serie_A/NucleusEA_v3_A3.mq5` | Momentum a 12 mesi, 5 mercati, 2010-2022 | Bocciato: -1,07% in 13 anni, 1 mercato su 5 positivo |
| B | 1 | `EA/Serie_B/NucleusEA_B1.mq5` | Rottura e retest dei livelli del giorno prima, XAUUSD | Bocciato: stop di emergenza ad aprile 2018 |
| B | 2 | `EA/Serie_B/NucleusEA_B2.mq5` | Effetto notte e giorno dell'oro | Bocciato: stop di emergenza a novembre 2017 |
| B | 3 | non ancora scritto | Ultimo tentativo della Serie B | In attesa di decisione |
| C | 1 | non scritto (`Scrematura_Python/screen_c1.py`) | Candela avvolgente M15 a favore del trend H1, target 1R, 15:00-18:45 server | Bocciato nella scrematura (14/10/2026): 1.379 operazioni, -221,8 R con costi doppi, +16,7 R senza costi, tutti gli anni negativi |
| D | 1 | `EA/Serie_D/NucleusEA_D1.mq5` (+ `Scrematura_Python/sim_d1_raddoppio.py`) | Obiettivo raddoppio: tendenza a 200 giorni su D1, volatilita' 25%, leva max 3 | Bocciato nella simulazione (14/10/2026): da 10.000 a 6.810 euro con costi doppi, stop di emergenza al 40% nel 2017. Test MT5 di conferma in attesa |
| E | 1 | non scritto (`Scrematura_Python/screen_e.py`) | Rottura delle 24 ore su H1, stop 2 x ATR, uscita con trailing stop 2,5 x ATR (skill exit-strategies di agiprolabs) | Bocciato nella scrematura (20/10/2026): 1.246 operazioni, -74,4 R con costi doppi, +49,8 R senza costi, vendite -66,4 R |
| E | 2 | non scritto (`Scrematura_Python/screen_e.py`) | Stessa entrata, uscita a fette: 25% a 2R, 3R, 5R, ultimo 25% con trailing | Bocciato nella scrematura (20/10/2026): 896 operazioni, -0,8 R con costi doppi, +97,3 R senza costi; acquisti +52,8 R, vendite -53,6 R |
| F | 1 | non scritto (`Scrematura_Python/screen_FGH.py`) | Apertura di New York: movimento 15:30-17:30 server di almeno 0,25%, si segue fino alle 22:55 | Bocciato nella scrematura (20/10/2026): 785 operazioni, -36,6 R con costi doppi, +5,0 R senza costi |
| G | 1 | non scritto (`Scrematura_Python/screen_FGH.py`) | Dollaro: oro comprato o venduto per 24 ore dopo un movimento dell'euro/dollaro BCE di almeno 0,5% | Bocciato nella scrematura (20/10/2026): 414 operazioni, -4,6 R con costi doppi, +6,1 R senza costi; acquisti -10,8 R |
| H | 1 | non scritto (`Scrematura_Python/screen_FGH.py`) | Rimbalzo: contro un giorno di almeno 1 ATR, il giorno dopo dalle 01:00 alle 22:55 | Bocciato nella scrematura (20/10/2026): 204 operazioni, -16,5 R con costi doppi, -10,0 R senza costi |

`EA/Serie_A/NucleusEA_v1.mq5` e' la primissima versione (EURUSD), poi adattata all'oro nella v1.1.

Idee provate in totale: 12 (i 9 tentativi sopra piu' 3 idee scartate nella scrematura in Python del 09/10/2026).

## Decisione del 20/10/2026: pausa delle nuove idee di trading

L'autore ha scelto l'opzione A nel thread "Valutazione generale di Nucleus" (giudizio in `../2_Nucleus_e_Blueprint/Audit/Valutazione_generale_Nucleus_2026-10-18.md`): nessuna nuova serie o idea di trading fino al 20/01/2027 almeno. Nel frattempo: portafoglio di carta C da novembre 2026, ordine nel repository, correzione per il numero di idee provate nella skill nucleus-test-ea. B3 e il test MT5 di conferma di D1 restano fermi.

## Sottocartelle

- `EA/` codice sorgente degli EA. Le copie usate da MT5 stanno sul Mac in `~/Nucleus/mt5/Experts`.
- `Strumenti/NucleusExport.mq5` EA che non opera: salva lo storico delle candele in CSV durante un test.
- `Risultati_test/` registri CSV dei test (una riga per operazione).
  - `B1_TESTER_XAUUSD.csv` contiene il test B1 ripetuto due volte (righe duplicate): usare solo la prima meta'.
  - `B2_v1.00_NON_VALIDO...` test con l'errore di orario, da non usare per giudicare.
  - `EURUSD_BTC_campagna_2026-10-20_riepilogo.csv` una riga per prova (non per operazione) della campagna su EUR/USD e Bitcoin; le operazioni sono nella cartella della campagna.
- `Dati/XAUUSD_M5_2016-2022.csv` storico dell'oro a 5 minuti del broker (ora server GMT+2/+3). Il 2023-oggi e' la cassaforte e non e' incluso.
- `Scrematura_Python/screen_b3.py` prova veloce di idee sullo storico, prima di scrivere un EA.
- `Prove_EURUSD_Crypto_2026-10-20/` prove esplorative su EUR/USD e Bitcoin (20/10/2026; non contano come tentativi Nucleus): 79 prove, nessuna supera i criteri. Riepilogo in euro per l'autore in `RIEPILOGO_ECONOMICO.md`, dettagli tecnici in `README.md`.

## Come si fa un test (procedura fissa)

1. Claude scrive i criteri nel Manuale, prima del test.
2. Claude scrive l'EA e lo mette nella cartella Nucleus di MT5.
3. Tu: MetaEditor, apri l'EA, premi F7. Strategy Tester, scegli l'EA, Avvia. Scrivi "fatto".
4. Claude legge il CSV, controlla che il test sia valido e da' il verdetto.

Regola tecnica imparata: le regole da non ottimizzare vanno scritte nel codice come costanti, perche' il tester ricorda i "Dati in ingresso" dei test precedenti.
