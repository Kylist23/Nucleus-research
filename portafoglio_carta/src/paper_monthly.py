"""Aggiornamento mensile del portafoglio di carta C (docs/STRADA1_PORTAFOGLIO_CARTA.md).

Uso, dalla cartella ~/Nucleus, dopo aver scaricato a mano l'oro da Stooq in Safari:
    .venv/bin/python -m src.paper_monthly ~/Downloads/xauusd_d.csv

1. Scarica dalla BCE le 5 serie mensili, solo dal mese d'acquisto (PAPER_START) in poi:
   i file nuovi non contengono nessun mese della cassaforte.
2. Importa in data/raw/stooq il file dell'oro scaricato a mano (copia identica, SHA-256).
3. Ricostruisce data/processed/paper_c_monthly.csv (src/build_paper_monthly.py).
4. Rigenera la pagina paper/index.html (src/paper_dashboard.py).

Ogni download e importazione segue le Regole dei dati di CLAUDE.md (nome unico, SHA-256,
registro dei tentativi). Se un passo fallisce ci si ferma: la tabella resta quella di prima.
Nessun denaro vero, nessun ordine, nessun conto collegato.
"""

from pathlib import Path
from datetime import datetime, timezone
import sys

from src import acquire_ecb
from src import build_paper_monthly as bpm
from src import import_manual
from src import paper_dashboard
from src.hashing import sha256_file
from src.path1_paper import PAPER_START


ECB_DESCRIPTIONS = {
    "spx_usd": "S&P 500 price index, monthly average of closes (USD), paper portfolio C",
    "sx5e_eur": "Euro Stoxx 50 price index, monthly average (EUR), paper portfolio C",
    "y10_pct": "Euro area long-term interest rate, 10-year government bonds, monthly (%), paper portfolio C",
    "euribor3m_pct": "Euribor 3 months, monthly average (%), paper portfolio C",
    "usd_per_eur": "US dollar per euro, monthly average, paper portfolio C",
}
GOLD_NAME = "xauusd_d.csv"
GOLD_MAX_AGE_DAYS = 3  # un file più vecchio è quasi certamente quello del mese prima


def ecb_url(series_id: str) -> str:
    """'FM.M.US.USD.DS.EI.S_PCOMP.HSTA' -> URL BCE con startPeriod = PAPER_START."""
    flow, key = series_id.split(".", 1)
    return (f"https://data-api.ecb.europa.eu/service/data/{flow}/{key}"
            f"?startPeriod={PAPER_START}&format=csvdata")


def download_ecb(raw_dir: Path = bpm.RAW, fetch=None) -> list[dict]:
    out = []
    for col, series_id in bpm.ECB_SERIES.items():
        meta = acquire_ecb.run(
            output_dir=raw_dir / "ecb",
            url=ecb_url(series_id),
            fetch=fetch,
            series_id=series_id,
            description=ECB_DESCRIPTIONS[col],
            start_period=PAPER_START,
        )
        print(f"BCE {col}: {meta['raw_file']} ({meta['row_count']} righe)")
        out.append(meta)
    return out


def import_gold(original: Path, raw_dir: Path = bpm.RAW, now: datetime | None = None) -> dict:
    original = Path(original).expanduser()
    if original.name != GOLD_NAME:
        raise ValueError(f"Il file dell'oro deve chiamarsi {GOLD_NAME}, non {original.name}")
    modified = datetime.fromtimestamp(original.stat().st_mtime, tz=timezone.utc)
    age_days = ((now or datetime.now(timezone.utc)) - modified).total_seconds() / 86400
    if age_days > GOLD_MAX_AGE_DAYS:
        raise ValueError(
            f"{original} è di {age_days:.0f} giorni fa: scarica di nuovo l'oro da Stooq "
            f"(e cancella prima il file vecchio, altrimenti Safari salva xauusd_d-2.csv)"
        )
    meta = import_manual.import_file(
        original,
        expected_sha256=sha256_file(original),
        source_id="stooq",
        output_dir=raw_dir / "stooq",
        description="Gold spot USD per troy ounce, daily (Stooq xauusd), paper portfolio C",
    )
    print(f"Oro Stooq: {meta['raw_file']} ({meta['row_count']} righe)")
    return meta


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("Uso: .venv/bin/python -m src.paper_monthly ~/Downloads/xauusd_d.csv")
        raise SystemExit(2)
    download_ecb()
    import_gold(Path(argv[0]))
    bpm.main()
    paper_dashboard.main()


if __name__ == "__main__":
    main()
