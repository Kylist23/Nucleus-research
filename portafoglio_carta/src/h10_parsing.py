"""Lettura del CSV Federal Reserve H.10.

Il file ha alcune righe di intestazione descrittiva prima della vera riga di colonne
(quella che comincia con "Time Period"). Il numero di quelle righe non è garantito:
cerchiamo la riga di colonne per contenuto, mai per un numero fisso di righe da saltare.
Allo stesso modo, la colonna della serie EUR si cerca per nome esatto, non per
sottostringa (così non rischiamo di prendere una colonna sbagliata che contenga "EU").
"""

from pathlib import Path
import csv

EUR_SERIES_KEY = "RXI$US_N.B.EU"


def find_header_row(rows: list[list[str]]) -> int:
    """Indice della riga che contiene i nomi delle colonne (comincia con "Time Period")."""
    for i, row in enumerate(rows):
        if row and row[0] == "Time Period":
            return i

    raise ValueError('Riga di intestazione "Time Period" non trovata nel file H.10.')


def get_series_column(header: list[str], series_key: str = EUR_SERIES_KEY) -> int:
    """Indice della colonna che corrisponde esattamente a `series_key`."""
    try:
        return header.index(series_key)
    except ValueError:
        raise ValueError(
            f"Colonna {series_key!r} non trovata tra le intestazioni: {header}"
        )


def load_eur_series(
    path: Path, series_key: str = EUR_SERIES_KEY
) -> list[tuple[str, str]]:
    """Restituisce la lista (data, valore testuale) per la serie EUR del file H.10.
    Il valore resta testo: può essere "ND" (dato mancante) o un numero."""
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))

    header_index = find_header_row(rows)
    header = rows[header_index]
    series_column = get_series_column(header, series_key)

    observations = []

    for row in rows[header_index + 1 :]:
        if not row:
            continue

        observations.append((row[0], row[series_column]))

    return observations
