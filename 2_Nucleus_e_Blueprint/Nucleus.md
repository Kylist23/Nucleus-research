**Nucleus** è un progetto personale su macOS che stiamo costruendo come laboratorio di ricerca finanziaria automatizzata. L'obiettivo di lungo periodo è creare un sistema composto da agenti AI specializzati — con supervisione/orchestrazione centrale — capace di analizzare mercati e dati finanziari, confrontare fonti, ricercare strategie, valutarne criticamente i risultati e, solo dopo una validazione molto rigorosa, supportare decisioni operative sugli investimenti. Il progetto parte da EUR/USD e dati giornalieri, con possibile estensione futura ad altri strumenti come oro, FX e altri mercati.

Il principio fondamentale è **controllo e sicurezza prima dell'autonomia e del profitto**: niente profitti garantiti, niente implementazione prematura e ogni risultato deve poter essere tracciato, verificato e sottoposto ad analisi avversariale. Il sistema dovrà progressivamente gestire provenienza e qualità dei dati, rischio, resilienza, auditabilità, sicurezza, agenti, orchestrazione, costi e autonomia.

Il progetto è organizzato in tre aree coordinate:
- **BLUEPRINT** — fonte di verità e archivio permanente di principi, decisioni, architettura e stato;
- **PROGETTO NUCLEUS** — sviluppo operativo e implementazione;
- **SVILUPPO E RICERCA** — ricerca, rischi, alternative e opportunità.

Il processo di sviluppo è:

**ANALISI → AUDIT AVVERSARIALE → VERIFICA → DECISIONE → BLUEPRINT → IMPLEMENTAZIONE**

con una catena operativa **ChatGPT ↔ Claude**: ChatGPT determina il passo successivo e prepara il prompt specifico per Claude; Claude esegue il compito e prepara a sua volta il prompt specifico per la verifica successiva di ChatGPT.

### Stato attuale

Abbiamo già chiuso e approvato:
- **Decisione 1 — RAW Acquisition Identity**
- **Decisione 2 — Acquisition Request & Attempt Model**

Entrambe sono state sottoposte ad analisi e revisione avversariale e registrate nel Blueprint.

È stato inoltre completato un **Implementation Audit**, dal quale è emerso che D1/D2 **non sono ancora implementate nel repository**: il codice ECB/H.10 esistente precede tali decisioni.

È stato verificato anche l'**Articolo 10 della Decisione 2** direttamente sul Blueprint originale, risultando conforme.

Attualmente siamo nella fase **Global Problem & Risk Audit**. Claude ha prodotto un audit globale con 47 voci tra problemi attuali, rischi futuri, gap, assunzioni e questioni rinviate. Il suo verdetto preliminare è "A — nessun blocker identificato", ma questo verdetto deve essere sottoposto alla verifica avversariale di ChatGPT e non viene considerato automaticamente valido.

Il prossimo obiettivo è quindi completare la **verifica avversariale del Global Problem & Risk Audit**.

Dopo questa verifica valuteremo anche se il Blueprint attuale debba essere:
**mantenuto, ristrutturato oppure ricostruito**, ma questa scelta non è ancora stata presa.

**Decisione 3 non è ancora iniziata.**