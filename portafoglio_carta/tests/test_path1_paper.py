"""Test del portafoglio di carta C (docs/STRADA1_PORTAFOGLIO_CARTA.md), solo su prezzi inventati.
I risultati attesi sono calcolati a mano: i passaggi sono nei commenti."""

from datetime import datetime, timezone

import pandas as pd
import pytest

from src import path1_backtest as bt
from src import path1_paper as paper


def _table(last="2026-12", start=paper.PAPER_START, y10=4.0, euribor=0.0, drops=None):
    """Prezzi fermi a 100 (salvo `drops`: {mese: fattore} applicato da quel mese in poi
    a S&P 500, Euro Stoxx 50 e oro), tasso a 10 anni e Euribor costanti."""
    months = bt.months_between(start, last)
    level = 100.0
    rows = []
    for m in months:
        if drops and m in drops:
            level *= drops[m]
        rows.append({"month": m, "spx_eur": level, "sx5e_eur": level, "gold_eur": level,
                     "y10_pct": y10, "euribor3m_pct": euribor})
    return pd.DataFrame(rows)


LATER = datetime(2031, 1, 1, tzinfo=timezone.utc)  # "oggi" dei test: tutti i mesi inventati sono finiti


def _status(table):
    return paper.paper_status(table, now=LATER)


K = 10_000.0
H0 = K / 1.001  # capitale investito dopo il costo d'acquisto dello 0,10%
STAMP = 1 - 0.002 / 12


# ------------------------------------------------------------------ la cassaforte resta chiusa

def test_rejects_vault_months():
    t = _table(start="2024-05", last="2026-12")
    with pytest.raises(paper.PaperWindowError, match="2024-05"):
        _status(t)


def test_rejects_month_just_before_start():
    t = _table(start="2026-10", last="2026-12")
    with pytest.raises(paper.PaperWindowError, match="2026-10"):
        _status(t)


def test_rejects_table_starting_after_start():
    t = _table(start="2026-12", last="2027-02")
    with pytest.raises(ValueError, match="deve partire da 2026-11"):
        _status(t)


def test_rejects_missing_month():
    t = _table(last="2027-02")
    t = t[t["month"] != "2026-12"]
    with pytest.raises(ValueError, match="consecutivi"):
        _status(t)


# ------------------------------------------------------------------ valori calcolati a mano

def test_purchase_month_only():
    s = _status(_table(last="2026-11"))
    c = s["portfolios"]["C"]
    assert s["months_of_returns"] == 0
    assert c["value"] == K and c["total_return"] == 0.0 and c["month_return"] is None
    # vendendo subito: H0 meno lo 0,10% di costo di vendita, nessuna tassa
    assert c["net_if_sold"] == pytest.approx(H0 * 0.999, abs=1e-9)


def test_c_one_month_flat_prices():
    # 2026-12: azioni e oro fermi, obbligazioni 4%/12 (tasso fermo), liquidità 0 (Euribor 0)
    s = _status(_table(last="2026-12"))
    expected = H0 * STAMP * (
        0.175 * (1 - 0.0020) ** (1 / 12)
        + 0.075 * (1 - 0.0020) ** (1 / 12)
        + 0.25 * (1 + 0.04 / 12) * (1 - 0.0015) ** (1 / 12)
        + 0.25 * (1 - 0.0025) ** (1 / 12)
        + 0.25
    )
    c = s["portfolios"]["C"]
    assert c["value"] == pytest.approx(expected, abs=1e-9)
    assert c["month_return"] == pytest.approx(expected / K - 1, abs=1e-12)
    assert s["december_before_rebalance"] is True


def test_liq_one_month_euribor_3():
    # liquidità: rendimento 3%/12 dall'Euribor del mese prima, poi il bollo
    s = _status(_table(last="2026-12", euribor=3.0))
    assert s["portfolios"]["LIQ"]["value"] == pytest.approx(H0 * (1 + 0.03 / 12) * STAMP, abs=1e-9)


def test_same_path_as_backtest_simulator():
    t = _table(last="2027-06", drops={"2027-02": 0.9, "2027-04": 1.2})
    s = _status(t)
    r = bt.monthly_returns(t.assign(btc_eur=float("nan")), allow_vault=True)
    sim = bt.simulate(r, bt.PORTFOLIOS["C"], "2026-11", "2027-06", K, allow_vault=True)
    assert s["portfolios"]["C"]["values"] == sim.values
    assert s["portfolios"]["C"]["net_if_sold"] == sim.final_net


# ------------------------------------------------------------------ quando si giudica

def test_no_judgment_before_12_months():
    assert _status(_table(last="2027-10"))["judgment_allowed"] is False  # 11 rendimenti
    assert _status(_table(last="2027-11"))["judgment_allowed"] is True   # 12 rendimenti


def test_alarm_above_15_percent_drawdown():
    # azioni e oro (50% di C) dimezzano: C scende di circa il 25% -> allarme
    s = _status(_table(last="2027-02", drops={"2027-01": 0.5}))
    assert s["portfolios"]["C"]["drawdown_now"] > 0.20
    assert s["alarm"] is True


def test_no_alarm_on_small_fall():
    # azioni e oro -10%: C scende di circa il 5% -> nessun allarme
    s = _status(_table(last="2027-02", drops={"2027-01": 0.9}))
    assert 0.04 < s["portfolios"]["C"]["drawdown_now"] < 0.06
    assert s["alarm"] is False


def test_criteria_only_after_36_months():
    assert _status(_table(last="2029-10"))["criteria"] is None   # 35 rendimenti
    s = _status(_table(last="2029-11"))                            # 36 rendimenti
    crit = s["criteria"]
    # prezzi fermi, obbligazioni al 4%, liquidità a 0: C cresce, LIQ perde solo il bollo
    assert crit["checks"] == {"max_drawdown": True, "worst_year": True, "above_cash": True}
    assert crit["passes"] is True
    assert crit["growth_liq"] < 0 < crit["growth_c"]


def test_criteria_fail_on_big_crash():
    # azioni e oro a un quinto nel 2027: C perde circa il 40% -> calo oltre il 25%, anno sotto -20%
    s = _status(_table(last="2029-11", drops={"2027-03": 0.2}))
    crit = s["criteria"]
    assert crit["checks"]["max_drawdown"] is False
    assert crit["checks"]["worst_year"] is False
    assert crit["passes"] is False


# ------------------------------------------------------------------ mesi non ancora finiti

def test_rejects_current_month():
    t = _table(last="2027-03")
    now = datetime(2027, 3, 15, 12, 0, tzinfo=timezone.utc)
    with pytest.raises(paper.OpenMonthError, match="2027-03"):
        paper.paper_status(t, now=now)


def test_rejects_future_month():
    t = _table(last="2027-03")
    now = datetime(2027, 1, 31, 23, 59, tzinfo=timezone.utc)
    with pytest.raises(paper.OpenMonthError, match="2027-03"):
        paper.paper_status(t, now=now)


def test_accepts_month_just_finished():
    # il 1° aprile 2027 in UTC, marzo è finito
    t = _table(last="2027-03")
    now = datetime(2027, 4, 1, 0, 0, tzinfo=timezone.utc)
    assert paper.paper_status(t, now=now)["as_of"] == "2027-03"


def test_default_now_rejects_future_table():
    # senza `now` si usa l'ora attuale: una tabella fino al 2099 non può essere finita
    with pytest.raises(paper.OpenMonthError):
        paper.paper_status(_table(last="2099-12"))


# ------------------------------------------------------------------ solo anni solari completi

def test_only_full_calendar_years_count():
    # 36 rendimenti, 2026-12..2029-11: anni completi solo 2027 e 2028
    s = _status(_table(last="2029-11"))
    assert sorted(s["criteria"]["years"]) == [2027, 2028]


def test_one_bad_december_2026_does_not_fail_worst_year():
    # azioni e oro -45% a dicembre 2026: "anno" di un solo mese sotto -20%, ma non conta
    s = _status(_table(last="2029-11", drops={"2026-12": 0.55}))
    crit = s["criteria"]
    assert 2026 not in crit["years"]
    assert crit["checks"]["worst_year"] is True
    # il calo resta visto dal criterio del calo massimo
    assert s["portfolios"]["C"]["max_drawdown"] > 0.20


def test_full_year_crash_still_fails_worst_year():
    # stesso crollo ma a febbraio 2027, dentro un anno completo
    s = _status(_table(last="2029-11", drops={"2027-02": 0.55}))
    assert s["criteria"]["years"][2027] < -0.20
    assert s["criteria"]["checks"]["worst_year"] is False
