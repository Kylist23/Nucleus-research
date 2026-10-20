---
name: nucleus-test-ea
description: "Procedura fissa del Progetto Nucleus per ogni idea di trading e ogni EA MT5: revisione scettica, criteri prima, test, controlli, prove di robustezza, verdetto e registro."
---

# Idee e test di un EA nel Progetto Nucleus

L'autore è un principiante: spiega ogni passo in italiano semplice, con tono formale ma dandogli del tu, senza emoji, con i numeri. Gli agenti AI analizzano, non operano: mai aprire, modificare o chiudere operazioni e mai togliere il blocco dei conti reali dagli EA. Il passaggio al denaro reale lo fa solo l'autore, a mano, dopo almeno 3 mesi di demo.

## 0. Revisione scettica dell'idea (prima di scrivere codice)

- Riscrivi l'idea in 3 righe (quando entra, quando esce, quanto rischia) e chiedi all'autore di confermarla.
- Chiedi perché dovrebbe guadagnare: serve un motivo economico (chi perde dall'altra parte, e perché). "Su un grafico ha funzionato" non è un motivo.
- Indica dove fallisce di solito quel tipo di strategia: seguire il trend fallisce nei mercati laterali e per i costi; il ritorno alla media fallisce nei trend forti e nei gap; la rottura di un livello fallisce per le false rotture; gli effetti di orario falliscono perché i costi si mangiano il piccolo vantaggio.
- Controlla questi punti e dai a ognuno una gravità (bloccante, grave, minore) con il suo rimedio:
  - vedere il futuro per errore: in pandas usare il prezzo di chiusura di una candela prima che sia chiusa, shift sbagliati, dati BCE o Fed usati prima della loro data di pubblicazione;
  - troppi parametri rispetto alle operazioni attese;
  - campione piccolo: con 100 operazioni anche una strategia senza vantaggio può sembrare buona per caso;
  - costi dell'oro: spread variabile (più largo al cambio di giorno e sulle notizie), swap, gap del lunedì;
  - dipendenza da un solo periodo di mercato.
- Conta i tentativi: leggi nel Manuale quante idee sono già state provate (8 al 9 ottobre 2026). Ogni variante proposta per migliorare il risultato (regole o parametri cambiati) è un nuovo tentativo della stessa serie e conta nel limite di 3; le varianti di controllo del punto 5 non sono tentativi. Più idee si provano, più è facile trovarne una che sembra buona per caso: per questo le prove del punto 5 sono obbligatorie.
- Se trovi un problema bloccante, fermati e spiegalo. Non compiacere: ogni obiezione va scritta con il suo rimedio.

## 1. Criteri prima del test (prima di vedere qualsiasi dato)

- Controlla nel Manuale di riferimento Nucleus (documento privato, capitolo 8) a che tentativo della serie siamo. Massimo 3 per serie.
- Registra nel Manuale i criteri, con la data: XAUUSD dal 2016.01.01 al 2022.12.31 (la cassaforte, dal 2023 in poi, resta intatta); almeno 100 operazioni; risultato maggiore di zero con costi raddoppiati (spread, commissioni e swap pagati due volte: l'EA li stima e li mostra come Risultato dell'OnTester); acquisti e vendite entrambi positivi; 2016-2019 e 2020-2022 entrambi positivi; drawdown relativo sotto il 10%.
- Registra anche, sempre prima, le soglie delle prove di robustezza del punto 5.
- Se puoi, fai prima una scrematura in Python su 1_Bot/Dati/XAUUSD_M5_2016-2022.csv con lo stesso metro (multipli di R, costi pagati due volte): costa poco e può evitare di scrivere un EA inutile.

## 2. Scrivere l'EA

- Parti dalla struttura di 1_Bot/EA/Serie_B/NucleusEA_B2.mq5: protezioni, blocco dei conti reali, registro CSV, riepilogo per direzione e per anno.
- Nel Risultato dell'OnTester togli una seconda volta spread, commissioni e swap (lo swap solo quando è un costo). B2 non conta due volte lo swap perché chiude sempre prima del cambio di giorno: se l'EA nuovo tiene posizioni di notte, aggiungilo.
- Scrivi le regole fisse (orari, soglie) come #define, non come input: lo Strategy Tester ricorda i valori dei test precedenti.
- Metti la versione nel nome del registro (per esempio Nucleus_EAB3v100) e scrivilo in "Nucleus\\..." con FILE_COMMON.
- L'orario del server è un'ora avanti rispetto all'Italia. Il broker non esegue ordini sull'oro dalle 23:00 all'01:00 (ora del server), anche se i prezzi arrivano: nessuna entrata o uscita in quella fascia.
- All'avvio stampa i parametri chiave, così il registro mostra cosa è stato usato davvero.

## 3. Consegna e lancio

- Salva il sorgente nell'originale, ~/Nucleus/mt5/Experts/ (sul Mac direttamente; dal cloud con device_commit_files). Se lavori sul Mac, registra solo quel file con un commit git che citi la versione, seguendo le regole di CLAUDE.md. Se lavori dal cloud, aggiorna anche la copia in 1_Bot/EA/<serie>/ (sul Mac quella cartella non c'è) e scrivi nel riepilogo che sul Mac manca il commit.
- Dopo qualche secondo rileggi il file sul Mac: MetaEditor può riscriverci sopra la versione vecchia se il file era aperto. Se succede, ricopialo e chiedi all'autore di chiudere la scheda senza salvare.
- Se lavori sul Mac con Remote Control e la compilazione da riga di comando è già stata provata, compila tu e controlla che esistano il file .ex5 e il .log. Altrimenti scrivi all'autore questi passi, uno per riga:
  1) apri MetaEditor; nel pannello Navigatore apri Experts > Nucleus, fai doppio clic sull'EA e premi F7: in basso deve comparire "0 errors" (o "0 errori");
  2) in MetaTrader 5 apri lo Strategy Tester e imposta: Expert Nucleus\<EA>, simbolo XAUUSD, il timeframe previsto dalle regole, date dal 2016.01.01 al 2022.12.31, Forward: No, modellazione "1 minute OHLC", deposito 25000 EUR, leva 1:25;
  3) premi Avvia (Start);
  4) a test finito scrivimi "fatto".

## 4. Il test è valido? (prima del verdetto)

- Il CSV atteso esiste in ~/Nucleus/mt5/Files/ (se manca, è partito un altro EA).
- La colonna ea_version corrisponde alla versione nuova.
- Gli orari di entrata e di uscita sono quelli previsti dalle regole.
- Se il test è finito presto, cerca lo stop di emergenza (drawdown del 10%).
- Controlla il CSV prima di usarlo: numero di righe; che cosa rappresenta una riga (un'operazione o un singolo ingresso o uscita); valori vuoti; righe doppie (per esempio due test finiti nello stesso file, come è successo con B1); buchi nelle date; numeri salvati come testo.
- Ricalcola il risultato netto in due modi (somma del CSV e riepilogo dello Strategy Tester) e controlla a mano 2-3 operazioni. Nel report di MT5 "Total Deals" conta entrate e uscite, "Total Trades" solo le chiusure: non confonderli.
- Campanelli d'allarme: risultati troppo belli, percentuali esattamente 0% o 100%, valori identici in periodi diversi, orari confusi (l'ora del server MT5 non è l'ora italiana né quella dei dati BCE o Fed).

## 5. Verdetto e prove di robustezza

- Calcola: operazioni, risultato netto, risultato con costi raddoppiati, acquisti e vendite separati, netto per anno, 2016-2019 contro 2020-2022, drawdown, percentuale di operazioni vinte, guadagno medio per operazione dopo i costi.
- Ricorda all'autore che con poche operazioni si riconosce solo un vantaggio grande: con 30 operazioni quasi nulla si distingue dal caso, e anche con 100 una strategia senza vantaggio può sembrare buona.
- Basta un criterio del punto 1 non superato e l'idea è bocciata. Niente modifiche dei parametri dopo aver visto i risultati. Una correzione di esecuzione (un errore nel codice) si dichiara e si rilancia senza contare un nuovo tentativo.
- Se tutti i criteri sono superati, prima di qualsiasi demo servono tutte queste prove, con le soglie scritte al punto 1:
  - rilancio con la modellazione "Every tick based on real ticks": in "1 minute OHLC" e "Open prices only" stop e target vengono eseguiti al prezzo esatto, quindi i risultati sono troppo ottimisti;
  - varianti vicine dei parametri, per esempio stop dal 50% al 150%: la maggioranza deve restare sopra soglia (un altopiano, non un picco isolato);
  - controllo di stabilità, in pandas sul CSV delle operazioni: l'ultimo terzo del periodo (da settembre 2020 a dicembre 2022) deve restare sopra soglia. Non è una prova fuori campione, perché quei dati sono già stati usati nel test principale.
- I costi non hanno una prova a parte: il criterio del punto 1 li conta già due volte. Nel tester lo spread viene dai dati storici e non si può cambiare.
- L'unica prova davvero fuori campione è la cassaforte (dal 2023 in poi): resta intatta finché l'autore non decide per iscritto di usarla, una sola volta, con soglie scritte prima.
- Il verdetto più alto possibile è "passa alla demo per 3 mesi". Mai "pronta per il denaro reale".
- Dopo ogni verdetto, solo nella risposta in chat (mai nel Manuale, nei file o nelle email), aggiungi la riga "Da ricontrollare prima di fidarti del verdetto (puoi copiarle e mandarmele):" e 2-3 domande che l'autore possa mandarti così come sono, legate ai numeri di quel test, per esempio: "Le operazioni sono abbastanza per escludere il caso?", "Che modellazione e che spread ha usato il tester?", "Il periodo e le soglie erano stati fissati prima?". Le domande non propongono mai di cambiare parametri, periodo o criteri: un'idea bocciata resta bocciata, e una variante è un nuovo tentativo della stessa serie, con criteri scritti prima.

## 6. Registro

- Aggiorna il Manuale (registro delle serie, numero totale di idee, lezioni) e 1_Bot/README.md; copia il CSV in 1_Bot/Risultati_test/. Se lavori sul Mac e non puoi raggiungerli, scrivi nel riepilogo cosa resta da aggiornare.
- Per ogni idea bocciata scrivi 5 righe: ipotesi, regole, risultati, dove si è rotta, lezione.
- Rispondi all'autore in questo ordine: "In breve" con il verdetto; il perché, in parole semplici e con i numeri; le domande "Da ricontrollare"; per ultimo un solo "Prossimo passo".

Idee riprese e riscritte con parole nostre da quattro fonti pubbliche, lette per intero il 9 ottobre 2026: strategy-review (github.com/VictorIstrati/expert-advisor, commit b805c48), backtest-expert (github.com/tradermonty/claude-trading-skills, licenza MIT), discernment-nudge (github.com/anthropics/skills, licenza Apache 2.0) e il plugin data (github.com/anthropics/knowledge-work-plugins, licenza Apache 2.0). Nessun testo copiato.
