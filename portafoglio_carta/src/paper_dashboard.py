"""Pagina "app" del portafoglio di carta C (docs/STRADA1_PORTAFOGLIO_CARTA.md).

Scrive un unico file HTML, senza internet e senza pacchetti nuovi: tutto (stile e
grafici) è dentro la pagina. Si apre con un doppio clic dal collegamento sul Desktop.
Mostra solo numeri calcolati da src/path1_paper.py e dal rapporto del test storico.
Nessun denaro vero, nessun ordine.
"""

from pathlib import Path
from datetime import datetime, timezone
from html import escape
import json

import pandas as pd

from src import path1_backtest as bt
from src import path1_paper as paper


PAPER_TABLE = Path("data/processed/paper_c_monthly.csv")
HISTORY_REPORT = Path("data/reports/path1/path1_report_20261013T210038Z_069f6523.json")
OUTPUT = Path("paper/index.html")

ASSET_NAMES = {
    "spx": "S&P 500 (azioni USA)",
    "sx5e": "Euro Stoxx 50 (azioni Europa)",
    "bond": "Obbligazioni 10 anni",
    "gold": "Oro",
    "cash": "Liquidità",
    "btc": "Bitcoin",
}
ASSET_COLORS = {
    "spx": "#4f8cff", "sx5e": "#7b61ff", "bond": "#2ec4b6",
    "gold": "#f2b134", "cash": "#9aa4b2", "btc": "#ff8a3d",
}
MONTHS_IT = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
             "agosto", "settembre", "ottobre", "novembre", "dicembre"]


# ---------------------------------------------------------------- formattazione

def eur(x: float) -> str:
    """10000.5 -> '10.000,50 €'"""
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"


def pct(x: float, sign: bool = True) -> str:
    """0.0123 -> '+1,23%'; zero (anche -0) -> '0,00%'"""
    if round(x * 100, 2) == 0:
        return "0,00%"
    s = f"{x * 100:+.2f}" if sign else f"{x * 100:.2f}"
    return s.replace(".", ",") + "%"


def month_label(m: str) -> str:
    """'2026-11' -> 'novembre 2026'"""
    y, mm = m.split("-")
    return f"{MONTHS_IT[int(mm) - 1]} {y}"


def next_month(m: str) -> str:
    return (pd.Period(m, freq="M") + 1).strftime("%Y-%m")


def next_december(m: str) -> str:
    y, mm = m.split("-")
    return f"{y}-12" if int(mm) < 12 else f"{int(y) + 1}-12"


# ---------------------------------------------------------------- grafici SVG

def line_chart(series: dict, labels: list, width: int = 640, height: int = 220) -> str:
    """Linee semplici in SVG. `series`: nome -> (valori, colore)."""
    all_v = [v for vals, _ in series.values() for v in vals]
    lo, hi = min(all_v), max(all_v)
    if hi == lo:
        lo, hi = lo * 0.99, hi * 1.01
    pad = 32
    left = 84  # spazio per le etichette in euro
    n = len(labels)

    def xy(i, v):
        x = left + (width - left - pad) * (i / (n - 1) if n > 1 else 0.5)
        y = height - pad - (height - 2 * pad) * (v - lo) / (hi - lo)
        return x, y

    parts = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img">']
    for frac in (0, 0.5, 1):
        v = lo + (hi - lo) * frac
        _, y = xy(0, v)
        parts.append(f'<line x1="{left}" x2="{width - pad}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        parts.append(f'<text x="{left - 6}" y="{y + 4:.1f}" class="axis" text-anchor="end">'
                     f'{escape(eur(v).replace(",00 €", " €"))}</text>')
    for name, (vals, color) in series.items():
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (xy(i, v) for i, v in enumerate(vals)))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        x, y = xy(len(vals) - 1, vals[-1])
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}"/>')
    parts.append(f'<text x="{left}" y="{height - 8}" class="axis">{escape(month_label(labels[0]))}</text>')
    parts.append(f'<text x="{width - pad}" y="{height - 8}" class="axis" text-anchor="end">'
                 f'{escape(month_label(labels[-1]))}</text>')
    parts.append("</svg>")
    return "".join(parts)


def bar_chart(items: list, width: int = 640, height: int = 200) -> str:
    """Barre verso l'alto (verde) o verso il basso (rosso). `items`: (etichetta, valore)."""
    vmax = max(abs(v) for _, v in items) or 1
    pad = 24
    zero = height / 2
    bw = (width - 2 * pad) / len(items)
    parts = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img">',
             f'<line x1="{pad}" x2="{width - pad}" y1="{zero}" y2="{zero}" class="grid"/>']
    for i, (label, v) in enumerate(items):
        h = (height / 2 - pad) * abs(v) / vmax
        x = pad + i * bw + bw * 0.15
        y = zero - h if v >= 0 else zero
        cls = "up" if v >= 0 else "down"
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw * 0.7:.1f}" height="{h:.1f}" '
                     f'class="{cls}"><title>{escape(label)}: {escape(pct(v))}</title></rect>')
        if i % 3 == 0 or i == len(items) - 1:
            parts.append(f'<text x="{x + bw * 0.35:.1f}" y="{height - 4}" class="axis" '
                         f'text-anchor="middle">{escape(label)}</text>')
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------- sezioni

def _allocation(holdings: dict, weights: dict) -> str:
    total = sum(holdings.values())
    bar = "".join(
        f'<span style="width:{100 * v / total:.2f}%;background:{ASSET_COLORS[a]}"></span>'
        for a, v in holdings.items())
    rows = []
    for a, v in holdings.items():
        rows.append(
            f'<tr><td><i style="background:{ASSET_COLORS[a]}"></i>{escape(ASSET_NAMES[a])}</td>'
            f'<td class="num">{escape(eur(v))}</td>'
            f'<td class="num">{escape(pct(v / total, sign=False))}</td>'
            f'<td class="num muted">{escape(pct(weights[a], sign=False))}</td></tr>')
    return (f'<div class="stack">{bar}</div>'
            '<table><tr><th>Attività</th><th class="num">Valore</th><th class="num">Peso oggi</th>'
            f'<th class="num">Peso obiettivo</th></tr>{"".join(rows)}</table>')


def _history_section(report_path: Path) -> str:
    if not report_path.exists():
        return ""
    m = json.loads(report_path.read_text(encoding="utf-8"))["measures"]
    c = m["periods"]["long"]["portfolios"]["C"]["evaluation"]
    status = m["prudence"]["versions"]["prices"]["long"]["portfolios"]["C"]["status"]
    final = m["prudence"]["final"]
    years = sorted(c["calendar_years"].items())
    return f"""
<section class="card">
  <h2>Il passato: test {escape(c['start'][:4])}–{escape(c['end'][:4])}</h2>
  <p class="muted">Come si sarebbe comportato C con i prezzi veri, dopo costi e tasse
  (solo prezzi, senza dividendi). Il passato non garantisce il futuro.</p>
  <div class="kpis">
    <div><span>Da 10.000 € a</span><b>{escape(eur(c['final_net']))}</b></div>
    <div><span>Guadagno medio annuo</span><b>{escape(pct(c['annual_growth']))}</b></div>
    <div><span>Calo massimo</span><b class="down">{escape(pct(-c['max_drawdown']))}</b></div>
    <div><span>Anno peggiore</span><b class="down">{escape(pct(c['worst_year']))}</b></div>
  </div>
  <h3>Anno per anno</h3>
  {bar_chart([(y, v) for y, v in years])}
  <p class="muted">Esito del test per C: {escape(status)} (solo prezzi).
  Verdetto complessivo: {escape(final['sentence'])}</p>
</section>"""


def _waiting_section() -> str:
    invested = paper.K / (1 + bt.TRADE_COST)
    weights = bt.PORTFOLIOS["C"]
    holdings = {a: w * invested for a, w in weights.items() if w > 0}
    first_data = next_month(paper.PAPER_START)
    return f"""
<section class="card">
  <h2>In attesa del primo mese</h2>
  <p>La prova parte con l'acquisto di <b>{escape(month_label(paper.PAPER_START))}</b>.
  I numeri compaiono quando quel mese è chiuso e i dati sono pubblicati
  (all'inizio di {escape(month_label(first_data))}).</p>
  <h3>Come verranno investiti i 10.000 € finti</h3>
  <p class="muted">Costo d'acquisto 0,10%: si investono {escape(eur(invested))}.</p>
  {_allocation(holdings, weights)}
</section>"""


def _live_sections(status: dict) -> str:
    c = status["portfolios"]["C"]
    liq = status["portfolios"]["LIQ"]
    months = bt.months_between(status["start"], status["as_of"])
    month_ret = c["month_return"]
    cls = "up" if (month_ret or 0) >= 0 else "down"
    remaining = max(paper.JUDGE_AFTER_MONTHS - status["months_of_returns"], 0)
    notices = []
    if status["alarm"]:
        notices.append('<div class="alert">Allarme: C è sceso più del 15% sotto il suo massimo. '
                       'Ne parliamo: le regole non si cambiano per questo.</div>')
    if status["december_before_rebalance"]:
        notices.append('<div class="note">Valore di dicembre mostrato prima del ribilanciamento.</div>')
    judge = ("Si può iniziare a giudicare." if status["judgment_allowed"]
             else f"Nessun giudizio prima di 12 mesi: ne mancano {remaining}.")
    chart = (line_chart({"C": (c["values"], "#4f8cff"), "LIQ": (liq["values"], "#9aa4b2")}, months)
             if len(months) > 1 else "")
    return f"""
<section class="card hero">
  <span class="muted">Valore del portafoglio C al {escape(month_label(status['as_of']))}</span>
  <div class="big">{escape(eur(c['value']))}</div>
  <div class="{cls}">{escape(pct(month_ret) if month_ret is not None else '—')} nel mese ·
  {escape(pct(c['total_return']))} da inizio prova</div>
  {''.join(notices)}
  {chart}
  <div class="legend"><i style="background:#4f8cff"></i>C
  <i style="background:#9aa4b2"></i>LIQ (solo liquidità, metro di confronto)</div>
</section>
<section class="card">
  <div class="kpis">
    <div><span>Se vendessi tutto oggi</span><b>{escape(eur(c['net_if_sold']))}</b></div>
    <div><span>Calo dal massimo</span><b class="down">{escape(pct(-c['drawdown_now']))}</b></div>
    <div><span>LIQ, stesso periodo</span><b>{escape(pct(liq['total_return']))}</b></div>
    <div><span>Prossimo ribilanciamento</span><b>{escape(month_label(next_december(status['as_of'])))}</b></div>
  </div>
  <p class="muted">{escape(judge)}</p>
</section>
<section class="card">
  <h2>Composizione</h2>
  {_allocation(c['holdings'], bt.PORTFOLIOS['C'])}
</section>"""


CSS = """
:root{--bg:#0e1117;--card:#161b22;--text:#e6edf3;--muted:#8b949e;--up:#2ea043;--down:#f85149;--line:#30363d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:15px/1.5 -apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif}
header{padding:20px 16px 4px;max-width:760px;margin:auto}header h1{margin:0;font-size:20px}
main{max-width:760px;margin:auto;padding:8px 16px 40px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin:14px 0}
.big{font-size:40px;font-weight:700;letter-spacing:-.5px;margin:4px 0}
h2{font-size:17px;margin:0 0 8px}h3{font-size:14px;margin:16px 0 6px;color:var(--muted)}
.muted{color:var(--muted)}.up{color:var(--up)}.down{color:var(--down)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.kpis div{background:var(--bg);border-radius:10px;padding:10px}
.kpis span{display:block;color:var(--muted);font-size:12px}.kpis b{font-size:18px}
table{width:100%;border-collapse:collapse;margin-top:10px}td,th{padding:7px 4px;border-bottom:1px solid var(--line);text-align:left}
th{color:var(--muted);font-weight:500;font-size:12px}.num{text-align:right}
td i,.legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:8px}
.legend{color:var(--muted);font-size:12px;margin-top:6px}.legend i{margin-left:10px}
.stack{display:flex;height:12px;border-radius:6px;overflow:hidden;margin-top:6px}
.chart{width:100%;height:auto;margin-top:12px}.grid{stroke:var(--line)}
.axis{fill:var(--muted);font-size:11px}rect.up{fill:var(--up)}rect.down{fill:var(--down)}
.alert{background:#3d1d1d;color:#ffb4ae;border-radius:10px;padding:10px;margin-top:10px}
.note{background:#1d2a3d;color:#a9c7ff;border-radius:10px;padding:10px;margin-top:10px}
footer{color:var(--muted);font-size:12px;max-width:760px;margin:auto;padding:0 16px 30px}
"""


def render(status: dict | None, report_path: Path = HISTORY_REPORT,
           generated_at: datetime | None = None) -> str:
    """Pagina completa. `status` = path1_paper.paper_status(...) oppure None (nessun dato)."""
    generated_at = generated_at or datetime.now(timezone.utc)
    body = _live_sections(status) if status else _waiting_section()
    return f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nucleus · Portafoglio C</title><style>{CSS}</style></head>
<body>
<header><h1>Nucleus · Portafoglio C</h1>
<span class="muted">Portafoglio di carta: 10.000 € finti, nessun denaro vero, nessun ordine.</span></header>
<main>{body}{_history_section(report_path)}</main>
<footer>Pesi: 17,5% S&amp;P 500 · 7,5% Euro Stoxx 50 · 25% obbligazioni · 25% oro · 25% liquidità.
Costi, bollo e tasse come nel test (docs/STRADA1_SPEC_TEST.md). Regole della prova:
docs/STRADA1_PORTAFOGLIO_CARTA.md. Pagina generata il
{escape(generated_at.strftime('%d/%m/%Y %H:%M'))} UTC.</footer>
</body></html>
"""


def load_status(table_path: Path = PAPER_TABLE) -> dict | None:
    """Stato del portafoglio, oppure None se i dati della prova non ci sono ancora."""
    if not table_path.exists():
        return None
    table = pd.read_csv(table_path, dtype={"month": str}, float_precision="round_trip")
    return paper.paper_status(table)


def main() -> None:
    html = render(load_status())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Pagina: {OUTPUT.resolve()}")


if __name__ == "__main__":
    main()
