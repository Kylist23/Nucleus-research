# Strada 1: specifica dei test dei portafogli

Scritta il 13/10/2026 e salvata su Git **prima di qualsiasi calcolo sui risultati**.
I criteri sono quelli approvati dall'autore il 13/10/2026 (Manuale di riferimento, capitolo 9).
Questa nota li rende calcolabili senza ambiguità; non li cambia.

## 1. Dati di partenza (in `data/raw/`, con SHA-256 nei metadati)

| Serie | Fonte | Chiave o file | Unità |
|---|---|---|---|
| S&P 500, solo prezzo, media del mese | BCE | `FM.M.US.USD.DS.EI.S_PCOMP.HSTA` | punti, USD |
| Euro Stoxx 50, solo prezzo, media del mese | BCE | `FM.M.U2.EUR.DS.EI.DJES50I.HSTA` | punti, EUR |
| Titoli di Stato 10 anni area euro, media del mese | BCE | `IRS.M.I9.L.L40.CI.0000.EUR.N.Z` | % annuo |
| Euribor 3 mesi, media del mese | BCE | `FM.M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA` (già in `data/raw/ecb/ecb_20261013T155500Z_a31be243.csv`) | % annuo |
| Cambio, dollari per 1 euro, media del mese | BCE | `EXR.M.USD.EUR.SP00.A` | USD per EUR |
| Oro, giornaliero | Stooq, scaricato a mano dall'autore | `xauusd_d.csv`, SHA-256 `d17800fea4236b8d0c6cd4daff97ec02faa092378fcec065ddb74fb98fd12c5f` | USD per oncia |
| Bitcoin, giornaliero | Stooq, scaricato a mano dall'autore | `btcusd_d.csv`, SHA-256 `f7d92c56a0d430696d0cb7ce2a3ca482cf6ef5d4c07215bc52791e6db54b9a98` | USD |

- Le serie BCE si scaricano con `src/acquire_ecb.py` (nome unico, tentativo registrato).
- I due file di Stooq si importano con un piccolo script in `src/` che copia l'originale senza
  modificarlo, con nome unico e scrittura esclusiva, e registra nei metadati: SHA-256, dimensione,
  righe, metodo `manual_browser_download`, percorso e nome originale, ora di modifica originale (UTC),
  ora dell'importazione (UTC). Anche l'importazione va nel registro dei tentativi.
  Se lo SHA-256 dell'originale non è quello della tabella, ci si ferma.

## 2. Tabella mensile (`data/processed/path1_monthly.csv`)

- Una riga per mese, da `1999-01` a `2022-12` compreso. **Nessun mese dal 2023 in poi** (cassaforte).
- Colonne: `month` (AAAA-MM), `spx_usd`, `sx5e_eur`, `y10_pct`, `euribor3m_pct`, `usd_per_eur`,
  `gold_usd`, `btc_usd`, `spx_eur`, `gold_eur`, `btc_eur`.
- **Tutto è media del mese**, così tutte le serie sono misurate nello stesso momento.
  Oro e Bitcoin: media aritmetica delle chiusure giornaliere (`Close`) del mese di calendario.
- Conversione in euro: `prezzo_eur = prezzo_usd / usd_per_eur`.
- Un mese senza dati resta vuoto (NaN): mai zero, mai riempito con il mese vicino.
- Rieseguendo con gli stessi file si ottiene un file identico byte per byte.
- Controlli scritti in `data/reports/path1/quality_monthly.json`:
  - per ogni colonna: primo e ultimo mese con dati, minimo, massimo;
  - mesi mancanti dentro i periodi usati: devono essere 0 (tutte le colonne in 2001-01..2022-12,
    tranne il Bitcoin, che deve essere completo in 2014-01..2022-12); se no, ci si ferma;
  - mesi con variazione superiore al 30% (Bitcoin: 60%): elencati, non tolti;
  - confronto del cambio: media mensile del file giornaliero BCE già presente
    (`data/raw/ecb/eur_usd_ecb_raw.csv`) contro `EXR.M`; differenza massima sotto 0,0005, se no ci si ferma.

## 3. Rendimenti mensili (dal mese m-1 al mese m)

- Azioni, oro, Bitcoin: `P_m / P_(m-1) - 1`, in euro.
- Obbligazioni: titolo a 10 anni comprato alla pari nel mese m-1 (cedola annua `c = y_(m-1)/100`),
  rivalutato nel mese m al tasso `y = y_m/100`, con durata residua `n = 10 - 1/12` anni:
  - `prezzo = c/y * (1 - (1+y)^(-n)) + (1+y)^(-n)`; se `|y| < 1e-9`: `prezzo = c*n + 1`;
  - `rendimento = prezzo - 1 + c/12`.
  - Controlli a mano: tasso costante → rendimento `c/12`; tasso da 4% a 5% → circa −7,338%.
- Liquidità: `euribor3m_pct_(m-1) / 100 / 12` (può essere negativo).
- Nessun rendimento usa dati del mese m+1 o successivi.

## 4. Portafogli (pesi obiettivo)

| Codice | S&P 500 | Euro Stoxx 50 | Obbligazioni | Oro | Liquidità | Bitcoin |
|---|---|---|---|---|---|---|
| A | 70% | 30% | | | | |
| B | 42% | 18% | 40% | | | |
| C | 17,5% | 7,5% | 25% | 25% | 25% | |
| D | 38,5% | 16,5% | 20% | 10% | 10% | 5% |
| LIQ (solo metro di confronto) | | | | | 100% | |
| D-core (solo informazione) | 38,5% | 16,5% | 20% | 10% | 15% | |

Le azioni sono sempre 70% S&P 500 e 30% Euro Stoxx 50; la parte satellite di D conta come azioni.

## 5. Periodi

- A, B, C, LIQ, D-core: si investe nel mese `2001-01`, ultimo mese `2022-12` (263 passi mensili).
- D, e per il confronto anche A, B, C, LIQ: da `2014-01` a `2022-12` (107 passi).
- Il codice rifiuta con un errore qualsiasi mese dal `2023-01` in poi, a meno di un parametro
  esplicito `allow_vault=True`, che in questa fase non si usa mai.

## 6. Regole della simulazione

Capitale iniziale `K` (per esempio 10 000 €). Per ogni posizione si tengono il valore `h` e il costo
fiscale `B` (costo medio).

- **Mese iniziale:** si compra ai pesi obiettivo. Il costo dello 0,10% si paga dal capitale:
  si investe `K / 1,001`. Il costo fiscale `B` è l'importo investito, senza commissioni (prudente).
- **Ogni mese successivo, in quest'ordine:**
  1. rendimento del mese: `h = h * (1 + r)`;
  2. costo annuo del fondo, un dodicesimo al mese: `h = h * (1 - TER)^(1/12)`;
     TER: S&P 500 e Euro Stoxx 50 0,20%, obbligazioni 0,15%, oro 0,25%, Bitcoin 1,00%, liquidità 0%;
  3. bollo, un dodicesimo al mese: `h = h * (1 - 0,002/12)` e `B = B * (1 - 0,002/12)`;
  4. se il mese è dicembre e non è l'ultimo mese della simulazione: ribilanciamento:
     - `V` = somma dei valori; obiettivo `t_i = w_i * V`;
     - per ogni posizione sopra obiettivo si vende `s_i = h_i - t_i`; guadagno
       `g_i = s_i * (1 - B_i/h_i)` (calcolato prima della vendita); tassa `aliquota_i * max(g_i, 0)`;
       poi `B_i = B_i * (1 - s_i/h_i)` e `h_i = h_i - s_i`; costo `0,001 * s_i`;
     - incasso netto = vendite − tasse − costi; si compra nelle posizioni sotto obiettivo in
       proporzione a quanto manca (`t_j - h_j`), per un totale di `incasso / 1,001`; `B_j` cresce di quanto comprato.
  5. `V_m` = somma dei valori dopo questi passi (valore di mercato, quello che vedresti dal broker).
- **Fine della simulazione:** si vende tutto, con tasse sui guadagni e costo dello 0,10% → valore finale netto.
- **Tasse:** 26% su S&P 500, Euro Stoxx 50, oro, Bitcoin, liquidità; 12,5% sulle obbligazioni.
  Una perdita non paga tasse e non dà crediti per il futuro (semplificazione prudente).
- **Senza ribilanciamento** (solo informazione): uguale, ma il passo 4 non c'è mai.

## 7. Misure e criteri (in euro, dopo costi e tasse)

`V_0 = K` (prima del costo d'acquisto). Tutte le soglie sono incluse: "non oltre 25%" passa con 25,00%.

1. **Caduta massima:** il massimo di `1 - V_m / max(V_0..V_m)`. Passa se ≤ 25%.
2. **Anni solari:** per ogni anno, `V_dicembre / V_dicembre dell'anno prima - 1`; per il primo anno
   si parte da `V_0`. Passa se nessun anno è sotto −20%.
3. **Tempo sotto il massimo:** per ogni discesa, i mesi dal mese del massimo al primo mese in cui
   `V` torna almeno a quel massimo. Passa se nessuna discesa supera 60 mesi. Una discesa non ancora
   recuperata alla fine conta solo se ha già superato 60 mesi; altrimenti si scrive "non ancora recuperata".
4. **Guadagno medio annuo:** `(valore finale netto / K)^(12/passi) - 1`. Passa se è più alto di
   quello di LIQ sullo stesso periodo, calcolato con le stesse regole.
5. **Finestre di 5 anni:** per ogni mese di partenza `s` con `s + 60` entro la fine del periodo si
   rifà una simulazione nuova (stesse regole, ribilanciamento a dicembre, vendita finale al mese `s + 60`).
   Passa se in almeno il 90% delle finestre il valore finale netto è sopra `K`.
   Finestre: 204 nel periodo 2001–2022, 48 nel periodo 2014–2022.

Un portafoglio passa solo se passa tutti e 5 i criteri.

## 8. Chi vince

1. A, B, C si giudicano sul periodo 2001–2022. Tra quelli che passano vince il guadagno medio annuo
   più alto; se i primi due distano meno di 0,50 punti l'anno, vince quello con la caduta massima più piccola.
2. D si giudica sul periodo 2014–2022. Se passa, si confronta con il vincitore del punto 1 sullo stesso
   periodo 2014–2022, con la stessa regola. Nel rapporto si scrive sempre che D non ha attraversato il 2008.
3. Se nessuno passa, è un risultato valido: si registra e non si cambiano pesi, periodi o criteri.

## 9. Solo informazione (non cambia il verdetto)

- Versione senza ribilanciamento.
- D-core sul periodo 2001–2022: mostra come si sarebbe comportato il resto di D nel 2008.
- Versamenti mensili: 10 000 € all'inizio e 200 € alla fine di ogni mese successivo, investiti ai pesi
  obiettivo (costo 0,10%). Si mostrano: totale versato, valore finale netto, e il momento peggiore
  come perdita rispetto al totale versato fino a quel mese.
- Dividendi stimati (non sono dati, sono una stima fissata ora): +1,6% l'anno sull'S&P 500 e +2,8%
  l'anno sull'Euro Stoxx 50, aggiunti come un dodicesimo al mese al rendimento di prezzo.
  Servono solo a mostrare quanto pesa la mancanza dei dividendi.
- I valori non tengono conto dell'inflazione.

## 10. Controlli prima della prova sui dati veri

- Test in `tests/` che importano il codice di `src/`, su casi piccoli con prezzi inventati e risultato
  calcolato a mano, almeno: conversione in euro; formula delle obbligazioni (i due controlli del punto 3,
  e tasso vicino a zero); liquidità con il tasso del mese prima; medie mensili con mesi vuoti; posizione
  ferma (solo costi e bollo); tasse sul guadagno, 12,5% sulle obbligazioni, nessuna tassa sulle perdite;
  ribilanciamento di due posizioni; caduta massima, anni solari e tempo sotto il massimo su serie note;
  numero di finestre; blocco della cassaforte; un prezzo cambiato nel mese m+1 non cambia nessun valore
  fino al mese m; versamenti mensili.
- Revisione esterna del codice e una seconda implementazione indipendente, scritta solo da questa nota:
  le due devono dare gli stessi numeri su dati inventati prima di usare i dati veri.
- Poi una sola esecuzione sui dati veri. Il rapporto va in `data/reports/path1/` con ora UTC,
  commit Git e SHA-256 della tabella mensile.

## 11. Cosa non si fa

- Niente dati dal 2023 in poi. Niente ricerca di pesi o parametri migliori.
- Niente cambi di pesi, periodi o criteri dopo aver visto i risultati.
- Un errore nel codice trovato dopo l'esecuzione si dichiara, si corregge e si rilancia:
  non conta come un nuovo tentativo.

## 12. Precisazioni (13/10/2026, prima di qualsiasi risultato)

Punti che la prima stesura lasciava aperti. Valgono per tutte e due le implementazioni.

- **Controlli della tabella (§2):** per i tassi (`y10_pct`, `euribor3m_pct`) si elencano i mesi con una
  variazione oltre 1 punto percentuale in valore assoluto, non oltre il 30%: vicino allo zero la
  variazione percentuale non ha senso. Per le altre colonne resta il 30% (Bitcoin 60%).
- **Rendimento mancante:** se in un mese della simulazione manca il rendimento di una posizione con
  peso maggiore di zero, il programma si ferma con un errore. Mai contarlo come zero.
- **Tasse (§6):** il guadagno tassabile è `importo venduto − quota di B`; il costo dello 0,10% non lo riduce.
  Nel ribilanciamento gli obiettivi si calcolano su `V` prima di qualsiasi vendita.
- **Anni solari (§7.2):** solo gli anni il cui dicembre cade tra i mesi della simulazione dopo il primo;
  anche per l'ultimo dicembre si usa il valore di mercato `V_m`, non il valore finale netto.
- **Tempo sotto il massimo (§7.3):** un massimo è un mese in cui `V` è almeno pari a tutti i valori
  precedenti (anche `V_0 = K` conta). La discesa finisce al primo mese successivo con `V` almeno pari
  a quel massimo. Durata = differenza tra i due numeri di mese. Non passa se la durata è oltre 60 (60 passa).
- **Soglie:** si confrontano i numeri senza arrotondare. Criterio 5: valore finale netto strettamente
  sopra `K`, quota delle finestre almeno 0,90.
- **Chi vince (§8):** si guardano solo i primi due per guadagno medio annuo; distanza strettamente sotto
  0,005 → vince la caduta massima più piccola (a parità, il primo). Se D passa, si confronta con il
  vincitore del punto 1 usando i numeri di tutti e due sul 2014–2022, anche se su quel periodo il vincitore
  non passa tutti i criteri. Se nessuno tra A, B e C passa e D passa, vince D. Se D non passa, vince
  il vincitore del punto 1 (o nessuno).
- **LIQ:** si calcola come gli altri ma è solo il metro di confronto; non partecipa al verdetto.
- **Versamenti (§9):** 200 € alla fine di ogni mese dopo il primo, ultimo mese compreso, dopo l'eventuale
  ribilanciamento di dicembre; si investe `200 / 1,001` ai pesi obiettivo e `B` cresce di quanto investito.
  Momento peggiore = il minimo, su tutti i mesi compreso il mese 0, di `(V_m / versato_m) − 1`, dove
  `V_m` è il valore dopo il versamento di quel mese e `versato_m` è il totale versato fino a quel mese
  compreso (al mese 0: `V_0 = K` e `versato_0 = K`); a parità vale il mese più vecchio.
- **Senza ribilanciamento e dividendi stimati (§9):** costi del fondo e bollo restano; si mostrano valore
  finale netto, guadagno medio annuo e caduta massima. Dividendi: ogni mese si aggiunge `d/12` al
  rendimento di prezzo (S&P 500 `d = 0,016`, Euro Stoxx 50 `d = 0,028`); il ribilanciamento di dicembre
  resta come nella versione principale.
- **Che cosa misura `V_m`:** è il valore di mercato. Costi, bollo e tasse già pagate nei ribilanciamenti sono
  tolti; le tasse sui guadagni non ancora venduti no. Caduta massima, anni solari e tempo sotto il massimo
  usano `V_m`; valore finale netto, guadagno medio annuo e finestre di 5 anni sono dopo tutte le tasse.
- **Discese elencate (§7.3):** si elencano solo le discese vere, cioè quando `V` scende sotto il massimo;
  se più mesi di fila sono pari al massimo, il massimo della discesa è l'ultimo prima della discesa.
- **Lettura della tabella:** chi usa `path1_monthly.csv` controlla prima il suo SHA-256 e legge i numeri
  senza perdere cifre (in pandas `float_precision="round_trip"`). Le righe devono essere mesi consecutivi,
  in ordine e senza doppioni; un rendimento non finito o pari o sotto −100% ferma il programma.
- **Dati BCE:** nelle righe fino al 2022-12 servono `OBS_STATUS = A` e `COLLECTION = A` (media del periodo);
  se no, ci si ferma. I file grezzi usati hanno SHA-256 fissati nel codice.

## 13. Regole di prudenza (approvate dall'autore il 13/10/2026, prima di qualsiasi risultato)

Nate dalla revisione del metodo. Non cambiano pesi, periodi né i 5 criteri: possono solo rendere il
verdetto più prudente, mai far passare chi non passa.

1. **Due versioni del verdetto.** Tutto il §7 e il §8 si calcolano due volte: con i soli prezzi (come
   finora) e con i dividendi stimati del §9 (`d/12` al mese, con ribilanciamento). Se le due versioni danno
   lo stesso vincitore, quello è il vincitore. Se danno vincitori diversi (anche "nessuno" contro un nome),
   il vincitore finale è "nessuno" con stato "al limite", e si mostrano tutte e due.
2. **D deve reggere il 2008.** D può vincere solo se, nella stessa versione, D-core passa tutti e 5 i
   criteri sul periodo 2001–2022. Se no, D non può vincere e resta il vincitore del punto 1 del §8.
   Si mostra anche il contributo del Bitcoin: guadagno medio annuo di D meno quello di D-core sul
   periodo 2014–2022 (quindi D-core si calcola anche su quel periodo).
3. **Risultati al limite.** Un criterio è "al limite" se il suo valore cade in questa fascia, estremi compresi:
   - caduta massima tra 22% e 28%;
   - anno peggiore tra −22% e −18%;
   - discesa più lunga (anche non recuperata) tra 54 e 66 mesi;
   - quota delle finestre tra 0,87 e 0,93;
   - guadagno medio annuo meno quello di LIQ tra −0,005 e +0,005.
   Un portafoglio che passa è "netto" se nessun criterio è al limite, altrimenti "al limite".
   Nella scelta del vincitore (§8, punto 1 e punto 2) un portafoglio netto batte sempre uno al limite;
   tra portafogli con lo stesso stato vale la regola del §8. Il vincitore porta il suo stato.
4. **Stato finale:** "netto" solo se le due versioni danno lo stesso vincitore e in tutte e due è netto;
   "al limite" in ogni altro caso con un vincitore; "nessuno" se nessuno vince in nessuna delle due.
   La parola "al limite" deve comparire nella frase del verdetto.
