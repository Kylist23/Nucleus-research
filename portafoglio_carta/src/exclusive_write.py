"""Scrittura esclusiva: crea un file solo se non esiste già, non lo sovrascrive mai."""

from pathlib import Path


def write_exclusive(path: Path, data: bytes) -> None:
    """Crea `path` e ci scrive `data`. Se `path` esiste già, solleva FileExistsError
    e non tocca il contenuto esistente."""
    with path.open("xb") as f:
        f.write(data)


def write_text_exclusive(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Come write_exclusive, ma per testo (usata per i metadati JSON)."""
    with path.open("x", encoding=encoding) as f:
        f.write(text)
