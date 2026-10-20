"""Portafoglio di carta C della strada 1 (docs/STRADA1_PORTAFOGLIO_CARTA.md).

Segue C e LIQ mese per mese da PAPER_START in avanti, con le stesse regole del test
(path1_backtest). Rifiuta qualsiasi mese prima di PAPER_START: i mesi della cassaforte
2023-01..2026-10 non vengono mai letti. Nessun denaro vero, nessun ordine.
"""

from datetime import datetime, timezone

import pandas as pd

from src import path1_backtest as bt


PAPER_START = "2026-11"   # mese d'acquisto
PAPER_PORTFOLIOS = ["C", "LIQ"]
K = 10_000.0

JUDGE_AFTER_MONTHS = 12      # prima di 12 rendimenti: nessun giudizio
CRITERIA_AFTER_MONTHS = 36   # dopo 36 rendimenti: confronto con i criteri del test §7
ALARM_DRAWDOWN = 0.15        # allarme se C scende più del 15% sotto il suo massimo


class PaperWindowError(Exception):
    """La tabella contiene un mese prima dell'inizio della prova (cassaforte o passato)."""


class OpenMonthError(Exception):
    """La tabella contiene il mese in corso o un mese futuro: non è ancora finito."""


def current_month(now: datetime | None = None) -> str:
    """Mese in corso in UTC, come "AAAA-MM"."""
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m")


def check_paper_table(table: pd.DataFrame, now: datetime | None = None) -> list:
    """Controlla che la tabella parta esattamente da PAPER_START, con mesi consecutivi
    e tutti già finiti (nessun mese in corso o futuro, in UTC)."""
    months = list(table["month"])
    if not months:
        raise ValueError("La tabella è vuota")
    early = [m for m in months if m < PAPER_START]
    if early:
        raise PaperWindowError(
            f"Mesi prima di {PAPER_START} non ammessi nel portafoglio di carta: {early[0]}..{early[-1]}"
        )
    if months[0] != PAPER_START:
        raise ValueError(f"La tabella deve partire da {PAPER_START}, parte da {months[0]}")
    if months != bt.months_between(months[0], months[-1]):
        raise ValueError("I mesi della tabella devono essere unici, in ordine e consecutivi")
    open_month = current_month(now)
    if months[-1] >= open_month:
        raise OpenMonthError(
            f"Il mese {months[-1]} non è ancora finito (mese in corso: {open_month})"
        )
    return months


def _drawdown_now(values: list) -> float:
    """Calo dell'ultimo valore rispetto al massimo raggiunto."""
    return 1 - values[-1] / max(values)


def _portfolio_state(returns: pd.DataFrame, weights: dict, months: list) -> dict:
    if len(months) == 1:
        # solo il mese d'acquisto: nessun rendimento ancora
        invested = K / (1 + bt.TRADE_COST)
        return {
            "values": [K], "value": K, "month_return": None, "total_return": 0.0,
            "drawdown_now": 0.0, "max_drawdown": 0.0, "net_if_sold": invested * (1 - bt.TRADE_COST),
            "holdings": {a: w * invested for a, w in weights.items() if w > 0},
            "sim": None,
        }
    sim = bt.simulate(returns, weights, months[0], months[-1], K, allow_vault=True)
    v = sim.values
    return {
        "values": v,
        "value": v[-1],
        "month_return": v[-1] / v[-2] - 1,
        "total_return": v[-1] / K - 1,
        "drawdown_now": _drawdown_now(v),
        "max_drawdown": bt.max_drawdown(v),
        "net_if_sold": sim.final_net,
        "holdings": dict(sim.holdings[-1]),
        "sim": sim,
    }


def full_calendar_years(months: list, values: list) -> dict:
    """Rendimenti degli anni solari completi: da dicembre a dicembre, entrambi nella prova.
    Il primo anno (solo dicembre 2026) e l'ultimo, se non arriva a dicembre, non contano."""
    years = bt.calendar_year_returns(months, values)
    return {y: r for y, r in years.items() if f"{y - 1}-12" in months}


def criteria_after_36(c: dict, liq: dict) -> dict:
    """§7 del test, ridotto ai tre criteri scritti nelle regole del portafoglio di carta."""
    c_sim, liq_sim = c["sim"], liq["sim"]
    years = full_calendar_years(c_sim.months, c_sim.values)
    c_growth = bt.annual_growth(c_sim.final_net, K, c_sim.steps)
    liq_growth = bt.annual_growth(liq_sim.final_net, K, liq_sim.steps)
    checks = {
        "max_drawdown": c["max_drawdown"] <= bt.MAX_DRAWDOWN_LIMIT,
        "worst_year": all(r >= bt.WORST_YEAR_LIMIT for r in years.values()),
        "above_cash": c_growth > liq_growth,
    }
    return {"checks": checks, "passes": all(checks.values()),
            "growth_c": c_growth, "growth_liq": liq_growth, "years": years}


def paper_status(table: pd.DataFrame, now: datetime | None = None) -> dict:
    """Stato del portafoglio di carta all'ultimo mese della tabella.
    `now` serve solo ai test; normalmente è l'ora attuale in UTC."""
    months = check_paper_table(table, now)
    t = table.copy()
    if "btc_eur" not in t.columns:
        t["btc_eur"] = float("nan")   # C e LIQ non usano Bitcoin
    # i mesi sono già controllati qui sopra: nessuno è prima di PAPER_START
    returns = bt.monthly_returns(t, allow_vault=True)
    states = {n: _portfolio_state(returns, bt.PORTFOLIOS[n], months) for n in PAPER_PORTFOLIOS}
    steps = len(months) - 1
    c, liq = states["C"], states["LIQ"]
    out = {
        "start": PAPER_START,
        "as_of": months[-1],
        "months_of_returns": steps,
        "judgment_allowed": steps >= JUDGE_AFTER_MONTHS,
        "alarm": c["drawdown_now"] > ALARM_DRAWDOWN,
        "december_before_rebalance": months[-1].endswith("-12"),
        "portfolios": {n: {k: v for k, v in s.items() if k != "sim"} for n, s in states.items()},
        "criteria": criteria_after_36(c, liq) if steps >= CRITERIA_AFTER_MONTHS else None,
    }
    return out
