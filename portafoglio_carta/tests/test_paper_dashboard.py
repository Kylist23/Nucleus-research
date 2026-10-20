"""Pagina del portafoglio di carta C: provata su prezzi inventati, mai sui dati della prova."""

import math
import re

from datetime import datetime, timezone

import pandas as pd

from src import paper_dashboard as d
from src import path1_paper as paper


def _invented_paper_table(n_months=5):
    months = pd.period_range(paper.PAPER_START, periods=n_months, freq="M").strftime("%Y-%m")
    rows = []
    for i, m in enumerate(months):
        fx = 1.10
        rows.append({
            "month": m, "spx_usd": 5000 * (1 + 0.02 * i), "sx5e_eur": 5000 * (1 - 0.01 * i),
            "y10_pct": 3.0, "euribor3m_pct": 2.0, "usd_per_eur": fx,
            "gold_usd": 2500 * (1 + 0.03 * math.sin(i)), "btc_usd": math.nan,
        })
    t = pd.DataFrame(rows)
    t["spx_eur"] = t["spx_usd"] / t["usd_per_eur"]
    t["gold_eur"] = t["gold_usd"] / t["usd_per_eur"]
    t["btc_eur"] = math.nan
    return t


LATER = datetime(2031, 1, 1, tzinfo=timezone.utc)  # "oggi" dei test: tutti i mesi inventati sono finiti


def _status(table):
    return paper.paper_status(table, now=LATER)


def test_italian_number_format():
    assert d.eur(10000.5) == "10.000,50 €"
    assert d.eur(-1234567.891) == "-1.234.567,89 €"
    assert d.pct(0.0123) == "+1,23%"
    assert d.pct(-0.05) == "-5,00%"
    assert d.pct(0.25, sign=False) == "25,00%"
    assert d.month_label("2026-11") == "novembre 2026"
    assert d.next_december("2026-11") == "2026-12"
    assert d.next_december("2026-12") == "2027-12"


def test_waiting_page_without_data(tmp_path):
    html = d.render(None, report_path=tmp_path / "nessun_rapporto.json")
    assert "In attesa del primo mese" in html
    assert "novembre 2026" in html
    # 10.000 / 1,001 = 9.990,01 investiti; 25% oro = 2.497,50
    assert "9.990,01 €" in html
    assert "2.497,50 €" in html
    assert "Bitcoin" not in html  # C non ha Bitcoin


def test_live_page_on_invented_prices(tmp_path):
    status = _status(_invented_paper_table(5))
    html = d.render(status, report_path=tmp_path / "nessun_rapporto.json")
    c = status["portfolios"]["C"]
    assert d.eur(c["value"]) in html
    assert d.eur(c["net_if_sold"]) in html
    assert "Nessun giudizio prima di 12 mesi: ne mancano 8." in html  # 4 rendimenti
    assert "<polyline" in html
    # le posizioni sommano al valore del portafoglio
    assert sum(c["holdings"].values()) == __import__("pytest").approx(c["value"])
    assert set(c["holdings"]) == {"spx", "sx5e", "bond", "gold", "cash"}


def test_page_has_no_external_resources(tmp_path):
    html = d.render(_status(_invented_paper_table(3)),
                    report_path=tmp_path / "x.json")
    assert not re.search(r'(src|href)\s*=\s*"https?://', html)
    assert "<script" not in html


def test_history_section_reads_the_report():
    html = d.render(None)  # usa il rapporto del test storico già nel repository
    assert "Il passato: test 2001–2022" in html
    assert "Anno per anno" in html


def test_zero_is_never_negative():
    assert d.pct(-0.0) == "0,00%"
    assert d.pct(-0.00001) == "0,00%"


def test_desktop_launcher_opens_this_page():
    # l'icona sulla Scrivania deve lanciare questo modulo e aprire il file che scrive
    from pathlib import Path
    from src import paper_dashboard
    launcher = (Path(__file__).parent.parent / "scripts" / "Portafoglio di carta.command").read_text()
    assert "-m src.paper_dashboard" in launcher
    assert f'open "{paper_dashboard.OUTPUT.as_posix()}"' in launcher
