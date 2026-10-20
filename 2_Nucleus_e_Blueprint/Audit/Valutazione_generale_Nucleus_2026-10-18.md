# Valutazione generale del Progetto Nucleus (18/10/2026)

Scritta da Claude su richiesta dell'autore. Materiale letto: tutte le cartelle di la cartella del progetto, i 9 rami del repository GitHub `(repository privato)`, i 14 thread del progetto, e 6 repository GitHub esterni (solo lettura dei README e delle licenze: nulla installato, nulla eseguito).
Ogni numero cita il file da cui viene. "Verificato" = ricontrollato oggi sul file o con un calcolo; "Da verificare" = non ricontrollato.

## In breve

1. **L'idea di partenza, così come è scritta** ("un sistema che fa le scelte al posto mio, con agenti AI che sanno fare tutto"), **non è realistica** e i vostri stessi test lo dimostrano: 11 idee di trading provate, 11 bocciate.
2. **Il metodo che avete costruito invece è buono**, migliore di quello di quasi tutti i progetti amatoriali e di molti repository famosi che ho letto. È il vero valore di Nucleus.
3. **Ha senso proseguire, ma come laboratorio di studio e come investimento lento con regole** (strada 1, portafoglio di carta C). Non ha senso proseguire come macchina per fare soldi veloci o come "entrata extra".

---

## 1. Cosa dicono i numeri (tutti in soldi finti)

### 1.1 Trading sull'oro e sulle cripto: 11 idee, 11 bocciate

| Idea | Risultato | Fonte |
|---|---|---|
| A1 incrocio di medie H1 | -505 euro, fattore di profitto 0,84 | `1_Bot/README.md` |
| A2 rottura 20 giorni, 5 mercati | -21 R su 210 operazioni | `1_Bot/README.md` |
| A3 momentum 12 mesi, 5 mercati | -1,07% in 13 anni | `1_Bot/README.md` |
| B1 rottura e retest | -2.023,89 euro, stop di emergenza (Verificato: somma di profit+swap+commission delle prime 351 righe di `Risultati_test/B1_TESTER_XAUUSD.csv`) | come a sinistra |
| B2 effetto notte/giorno | -1.975,17 euro, stop di emergenza (Verificato: `Risultati_test/B2_v1.01_TESTER_XAUUSD.csv`, 1.934 righe) | come a sinistra |
| C1 candele M15 | -221,8 R con costi doppi, +16,7 R senza costi | `1_Bot/README.md`, `screen_c1.py` |
| D1 tendenza 200 giorni con leva | da 10.000 a 6.810 euro | `1_Bot/Report_raddoppio_2026-10-14.md` |
| 3 idee scartate in Python il 09/10 | bocciate | `1_Bot/README.md` |
| CR1 Bitcoin media 200 | bocciata: calo massimo -67,2% in dollari, robustezza 0/4 | `5_Ufficio_Cripto/Scrematura_Python/cr1_risultati.txt` |

Somma delle prove sull'oro misurate in euro: -7.694 euro finti (A1 + B1 + B2 + D1; B1 e B2 Verificati oggi, A1 e D1 dai report).

**Cosa significa, detto chiaro.** Non è sfortuna e non è un errore di programmazione. Il motivo si vede in `1_Bot/Proposte/Serie_C_candele_proposta.md`: sull'oro, pagando lo spread due volte, una regola con target di 1 $ deve vincere il 68% delle volte solo per pareggiare. C1 senza costi era leggermente positiva (+16,7 R), con i costi fortemente negativa. Il trading veloce di un privato sull'oro, con un CFD (contratto che segue il prezzo senza comprare oro vero), parte svantaggiato dai costi. Questo è un risultato vero e utile, non un fallimento del progetto.

**CR1 non è un successo nascosto.** 10.000 euro diventano 270.359, ma "compra e tieni" fa 260.020 (`cr1_euro_risultati.txt`). Il guadagno viene dal Bitcoin salito circa 26 volte, non dalla regola. E a un certo punto il conto perde il 57% (-359.249 euro dal picco).

### 1.2 Esperimenti "da 10 a 1000" e "raddoppio"

- x100 con 10 euro: con leva 20, il 96,2% delle partenze 1971-2017 finisce in rovina (`1_Bot/Scrematura_Python/x100_10euro_risultati.txt`).
- x10 con 100 euro: con leva 5, entro 10 anni, 30,3% di successi e 66% di rovine (`Esperimento_libero/REPORT_100_a_1000_2026-10-16.md`).
- Raddoppio "libero": il meglio onesto è stato quasi "compra l'oro e tienilo", x1,46 con lo swap reale (`Esperimento_libero/REPORT.md`).

Lezione: **il rendimento non si sceglie, si sceglie il rischio.** Ogni richiesta di moltiplicare piccoli capitali porta allo stesso muro.

### 1.3 L'unico risultato positivo: la strada 1 (investimento lungo con regole)

Fonte: `data/reports/path1/path1_report_20261013T210038Z_069f6523.json` sul ramo `strada1-portafoglio-carta` (Verificato: letto oggi). 10.000 euro, dopo costi e tasse, solo prezzi senza dividendi.

| Portafoglio | Periodo | Valore finale | Crescita annua | Calo massimo | Passa i 5 criteri? |
|---|---|---|---|---|---|
| C (25% oro, 25% obbligazioni, 25% liquidità, 25% azioni) | 2001-2022 | 20.802 euro | 3,4% | 9,0% | Sì |
| Liquidità (LIQ) | 2001-2022 | 11.881 euro | 0,8% | 4,0% | No |
| A (più azioni) | 2001-2022 | 15.120 euro | 1,9% | 59,8% | No |
| D (con 5% Bitcoin) | 2014-2022 | 25.978 euro | 11,3% | 16,3% | Sì, ma non ha attraversato il 2008 |

**Onestà su C:**
- 3,4% l'anno è poco. L'inflazione dell'area euro nel 2001-2022 è stata in media intorno al 2% l'anno (Da verificare con la serie HICP della BCE): il guadagno reale è circa 1-1,5% l'anno.
- C ha il 25% di oro in un periodo in cui l'oro è passato da circa 270 $ a circa 1.800 $ (Da verificare sul file Stooq). Chi ha scelto i pesi nel 2026 conosceva già questa storia: un po' di "senno di poi" c'è, anche se i criteri sono stati scritti prima del test (`docs/STRADA1_SPEC_TEST.md`, commit 63ca2e8).
- I dividendi mancano, quindi le azioni sono sottostimate. Questo penalizza A e D più di C.
- Per questo il portafoglio di carta da novembre 2026 è la scelta giusta: è l'unica prova che nessuno ha già visto.

---

## 2. Cosa funziona davvero (i punti di forza)

1. **Criteri scritti prima del test, sempre.** È la regola più importante della ricerca seria, e nei repository famosi che ho letto spesso manca.
2. **La cassaforte 2023-oggi.** Dati mai guardati, tenuti per la verifica finale. Il portafoglio di carta rifiuta per codice i mesi prima di novembre 2026 (thread "Test portafoglio di carta sul Mac").
3. **Costi pagati due volte.** È la ragione per cui C1 è stata bocciata invece di sembrare buona.
4. **Massimo 3 tentativi per serie e risultati negativi registrati.** Limita il "provare finché esce qualcosa".
5. **Il denaro reale non si tocca.** Nessuna operazione reale fatta: 0 euro guadagnati, 0 persi (`5_Ufficio_Cripto/Valutazione_fonti_e_conti_2026-10-17.md`).
6. **Lo scetticismo verso TikTok e corsi.** CO System, il bot "3 passi", l'EA di ChatGPT con il conto azzerato: tutti valutati e scartati con motivi (`3_Idee_GitHub/README.md`).
7. **Test automatici nel codice:** 169 test passati sul Mac per il portafoglio di carta (thread "Test portafoglio di carta sul Mac").

---

## 3. Cosa non funziona (i punti deboli, senza sconti)

1. **Troppe idee per capitale zero.** In 9 giorni (09/10-18/10) il progetto ha toccato: EUR/USD, oro M5, 5 mercati, portafogli, cripto, x100, x10, entrate extra, video TikTok. Ogni nuova idea consuma tempo e uso di Claude, e aumenta il rischio di trovarne una "buona per caso". Con 11 idee provate, una che passasse andrebbe comunque corretta per il numero di tentativi (vedi sezione 4).
2. **Lo scopo si sposta verso "soldi veloci".** Le richieste "10 euro a 1000", "raddoppio", "entrata extra con le cripto" vanno contro quello che i dati hanno già detto. Il rischio non è tecnico, è psicologico: un risultato bello per caso potrebbe convincerti a passare al reale.
3. **Il repository è disordinato.** `main` ha solo 4 commit (Verificato: `git log`); il lavoro vero è su 7 rami separati mai uniti (`strada1-portafoglio-carta` ha 33 commit non su main, thread "Test portafoglio di carta sul Mac"). Le copie in la cartella del progetto non si aggiornano da sole. Chi riprende il lavoro fa fatica a capire qual è la versione giusta.
4. **Burocrazia sproporzionata all'inizio.** Il Blueprint con la catena ChatGPT ↔ Claude, Decisioni 1 e 2 e un audit di 47 voci (`2_Nucleus_e_Blueprint/Nucleus.md`) per scaricare il cambio EUR/USD: tanto lavoro di regole prima di avere una domanda di ricerca. Il lavoro utile è arrivato dopo, quando le regole sono state semplificate.
5. **Gli "agenti AI" oggi non esistono nel progetto.** Ci sono script Python, EA in MQL5 e Claude che lavora nei thread. Va bene così, ma "agenti AI che sanno fare tutto" resta una descrizione, non una parte costruita.
6. **Dati limitati.** Oro M5 di un solo broker, spread 2021-2022 probabilmente sottostimato (`Serie_C_candele_proposta.md`), Bitcoin solo nei giorni feriali, indici senza dividendi.

---

## 4. Repository GitHub che possono valutare un progetto come Nucleus

Nessun repository "giudica un'idea" da solo: offrono metodi. Li ho letti, non installati. Stelle e licenze lette oggi da GitHub.

| Repository | Cosa fa, in parole semplici | Utile a Nucleus? | Rischi |
|---|---|---|---|
| [bashtage/arch](https://github.com/bashtage/arch) (1.601 stelle, licenza permissiva tipo NCSA) | Contiene il test SPA, detto anche "Reality Check": dice se la migliore di tante strategie batte un riferimento più di quanto farebbe la fortuna. Esempio: se provi 11 idee e una sembra buona, il test tiene conto delle altre 10. | **Sì, il più utile.** Va usato solo quando un'idea passa i criteri. | Basso: libreria accademica, senza rete. Va installata (pip): serve il tuo sì. |
| [esvhd/pypbo](https://github.com/esvhd/pypbo) (144 stelle, licenza AGPL-3.0) | Calcola la "probabilità di overfitting del backtest" (quanto è probabile che il migliore sul passato sia mediocre sul futuro) e il "Deflated Sharpe Ratio" (un Sharpe ridotto in base al numero di prove). Basato sugli articoli di López de Prado. | Sì come metodo. Meglio riscrivere le 20-30 righe della formula in pandas. | Medio: il README stesso dice "TODO: add test cases"; richiede statsmodels 0.8.0, molto vecchio; la licenza AGPL obbliga a pubblicare il codice se lo distribuisci. |
| [ranaroussi/quantstats](https://github.com/ranaroussi/quantstats) (7.720 stelle, Apache 2.0) | Crea un rapporto completo da una serie di rendimenti: Sharpe, calo massimo, mesi peggiori, Monte Carlo. | Sì per il portafoglio di carta C, quando ci saranno 12 mesi di dati. Era già nella lista di `3_Idee_GitHub/README.md`. | Basso. Da verificare se il rapporto HTML scarica risorse da internet. |
| [skfolio/skfolio](https://github.com/skfolio/skfolio) (2.516 stelle, BSD-3) | Prove di portafogli con "walk forward" (scegli sul passato, verifichi sul pezzo dopo, poi sposti la finestra) e prove di stress. | Più avanti, solo se si confrontano altri portafogli oltre a C. | Medio: è fatto per ottimizzare i pesi, cioè proprio la cosa che può creare risultati per caso. |
| [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (111.844 stelle, Apache 2.0) | Più AI con ruoli (analista, ricercatore, trader, gestore del rischio) che discutono e danno un giudizio su un'azione USA. | Solo come modello di organizzazione degli "agenti". Non valuta Nucleus. | Alto per te: servono chiavi API a pagamento; il README stesso dice che è "un'impalcatura di ricerca, non una strategia con un rendimento ripetibile". |
| [virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) (64.065 stelle, MIT) | "Fondo" di AI che imitano investitori famosi, con prova su carta. | No: azioni USA, chiavi API (Financial Datasets e un modello AI). | Il README dice "solo a scopo educativo, non per operare davvero". |
| Repository piccoli su overfitting (fluke, overfit, overfitting-audit-mcp, perception-xalpha-lite) | Promettono gli stessi calcoli di pypbo. | No. | 0-2 stelle, creati nel 2026, nessuno storico. Uno è un server MCP: codice con accesso agli strumenti di Claude. Scartati. |

Già valutati in passato e ancora validi: `tradermonty/claude-trading-skills` (backtest-expert copiata nel repository, `4_Crescita_idee_e_possibilita/Skill/Valutazione_skill_GitHub_2026-10-14.md`) e l'elenco `wilsonfreitas/awesome-quant`.

**Cosa direbbero questi metodi su Nucleus oggi (applicati a mano, senza eseguire codice).** Nessuna strategia di trading ha passato i criteri, quindi non c'è niente da "sgonfiare": SPA e PBO servirebbero solo se una passasse. La loro lezione vale già ora: dopo 11 idee, la prossima che sembra buona va trattata con più sospetto, non con meno.

---

## 5. È un'ottima idea? Ha senso andare avanti?

| Versione del progetto | Giudizio | Perché |
|---|---|---|
| Sistema che fa trading al posto tuo e genera guadagni | **No** | 11 idee su 11 bocciate; i costi dell'oro su CFD bastano a spiegarlo (sezione 1.1). |
| Fonte di "entrata extra" o moltiplicatore di piccoli capitali | **No** | x100 e x10 portano soprattutto alla rovina (sezione 1.2). |
| Investimento lungo con regole, seguito su carta | **Sì, con aspettative basse** | C ha passato i criteri; il portafoglio di carta è la prova onesta. Rendimento atteso modesto. |
| Laboratorio per imparare finanza, statistica, Python e AI | **Sì, ed è il valore più grande** | In 9 giorni hai imparato concetti (costi, leva, overfitting, cassaforte) che molti trader non conoscono dopo anni. |

Un'osservazione legale e pratica (Da verificare sulla pagina del tuo broker): i broker europei di CFD devono pubblicare la percentuale di clienti al dettaglio che perde denaro, e di solito è la maggioranza. Nucleus finora ti ha evitato di entrare in quella statistica.

## 6. Cosa consiglio (al massimo 3 opzioni)

1. **Consolidare (raccomandata).** Fermare nuove serie di trading per almeno 3 mesi. Seguire il portafoglio di carta C da novembre. Mettere ordine nel repository (portare i rami utili su `main`, dopo una revisione). Aggiungere al punto 5 della skill nucleus-test-ea il Deflated Sharpe Ratio scritto in pandas, senza installare nulla. Motivo: è l'unica strada con un risultato positivo e costa poco.
2. **Consolidare e provare i metodi esterni.** Come l'1, più installare `arch` e `quantstats` in un ambiente separato e provarli su dati già usati (per esempio i rendimenti mensili di C 2001-2022). Serve il tuo sì perché è codice esterno.
3. **Continuare a cercare idee di trading.** Sconsigliato: ogni idea in più rende meno credibile un eventuale successo, e i costi restano lo stesso ostacolo.

**Prossimo passo:** dimmi 1, 2 o 3.

## Decisione

20/10/2026: L'autore ha scelto A (equivale all'opzione 1 qui sopra). Registrata in `1_Bot/README.md`.
