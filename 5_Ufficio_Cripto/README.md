# 5. Ufficio Cripto

Strada parallela a Nucleus, dedicata solo alle cripto (decisione dell'autore, 17/10/2026).
Non e' una quota del portafoglio C della strada 1: ha regole, serie di test e registro propri.

## Regole dell'ufficio (le stesse di Nucleus)
- Nessun denaro reale, nessun ordine su exchange, mai chiavi API.
- Criteri scritti prima di ogni test; cassaforte 2023-01-01 / oggi intatta; massimo 3 tentativi per serie.
- Dopo un test superato: portafoglio di carta per almeno 3 mesi. Il passaggio ai soldi veri lo fa solo l'autore, a mano.

## Contenuto
| File | Cosa contiene |
|---|---|
| `Repository_cripto_2026-10-17.md` | Repository GitHub valutati: analisi, segnali e automazione del lavoro |
| `Proposte/Serie_CR_proposta.md` | Proposta CR1 con revisione scettica (criteri definitivi nel Manuale, cap. 10) |
| `Scrematura_Python/` | Script e risultati dei test (`cr1_risultati.txt` in dollari, `cr1_euro_risultati.txt` in euro, `cr1_curva.csv`, `cr1_operazioni_euro.csv`) |
| `Valutazione_fonti_e_conti_2026-10-17.md` | Quanto abbiamo fatto e perso in euro (soldi veri: 0) e valutazione delle fonti dei dati cripto, con conclusione |

Skill di analisi copiata nel repository: `.claude/skills/crypto-regime-analyzer/` (MIT, commit b29c6df, ramo claude/project-thread-mdli4j). Solo descrittiva. Per l'uso live serve la chiave Demo di CoinGecko (la crea l'autore, mai in chat) con una piccola modifica dichiarata; la parte Binance (tassi di finanziamento, 15% del punteggio, `scripts/scorer.py` riga 31) resta spenta perché Binance è esclusa: restano 5 parti su 6 (85% del peso), sopra il minimo della skill (4 parti e 65%).

## Dati
- Bitcoin giornaliero Stooq: `../1_Bot/Dati/Stooq_manuale_2026-10-13/btcusd_d.csv` (solo giorni feriali).
- Fonti proposte il 17/10/2026 e approvate dall'autore alle 19:15 UTC ("A fonti proposte da verificare e acquisire"): Coinbase (principale), Kraken e Stooq (controllo), CoinGecko (solo fotografia del mercato). Binance esclusa. Schede in `sources/` del repository. Verifica dei termini e scarico dei dati dal Mac: in attesa del consenso dell'autore sul Mac.

## Registro dei test
| Serie | Tentativo | Idea | Esito |
|---|---|---|---|
| CR | 1 | Bitcoin sopra o sotto la media a 200 giorni, decisione a fine settimana (`Scrematura_Python/cr1_media200.py`) | Bocciato (17/10/2026): calo massimo -67,2% (limite 50%), solo 15,8 punti meglio di compra e tieni (servivano 20); robustezza 0/4 |
