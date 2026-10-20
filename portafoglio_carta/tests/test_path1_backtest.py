"""Test del simulatore della strada 1 (spec §10), solo su prezzi inventati.
I risultati attesi sono calcolati a mano: i passaggi sono nei commenti."""

import json
import math

import pandas as pd
import pytest

from src import path1_backtest as bt
from src.hashing import sha256_file


# ------------------------------------------------------------------ aiuti

def _returns(months, **cols):
    """Tabella dei rendimenti: una colonna per attività, la prima riga è il mese d'acquisto."""
    data = {a: cols.get(a, [0.0] * len(months)) for a in bt.ASSETS}
    return pd.DataFrame(data, index=months)


def _fake_table(first="1999-01", last="2022-12", seed=7):
    """Prezzi inventati, deterministici, con su e giù."""
    months = bt.months_between(first, last)
    rows = []
    x = seed
    level = {"spx": 1000.0, "sx5e": 3000.0, "gold": 300.0, "btc": 100.0}
    for i, m in enumerate(months):
        x = (1103515245 * x + 12345) % (2 ** 31)
        u = x / 2 ** 31 - 0.5  # tra -0,5 e 0,5
        level["spx"] *= 1 + 0.08 * u + 0.004
        level["sx5e"] *= 1 - 0.06 * u + 0.002
        level["gold"] *= 1 + 0.03 * math.sin(i / 7)
        level["btc"] *= 1 + 0.25 * u + 0.01
        fx = 1.1 + 0.1 * math.sin(i / 13)
        rows.append({
            "month": m,
            "spx_usd": level["spx"], "sx5e_eur": level["sx5e"],
            "y10_pct": 3 + 2 * math.sin(i / 20), "euribor3m_pct": 1.5 + 1.8 * math.cos(i / 25),
            "usd_per_eur": fx, "gold_usd": level["gold"], "btc_usd": level["btc"],
        })
    t = pd.DataFrame(rows)
    t["spx_eur"] = t["spx_usd"] / t["usd_per_eur"]
    t["gold_eur"] = t["gold_usd"] / t["usd_per_eur"]
    t["btc_eur"] = t["btc_usd"] / t["usd_per_eur"]
    return t


K = 10_000.0
H0 = K / 1.001  # 9990,00999: capitale investito dopo il costo d'acquisto dello 0,10%


# ------------------------------------------------------------------ §3 rendimenti

def test_bond_constant_rate_returns_coupon_over_12():
    # tasso fermo al 4%: il titolo resta alla pari, rendimento = 0,04/12 = 0,003333
    assert bt.bond_return(4.0, 4.0) == pytest.approx(0.04 / 12, abs=1e-12)


def test_bond_rate_up_from_4_to_5():
    # c = 0,04, y = 0,05, n = 9,9166667
    # 1,05^-9,9166667 = e^(-9,9166667 * 0,04879016) = e^-0,48383577 = 0,6164144
    # prezzo = 0,04/0,05 * (1 - 0,6164144) + 0,6164144 = 0,3068685 + 0,6164144 = 0,9232829
    # rendimento = 0,9232829 - 1 + 0,04/12 = -0,0767171 + 0,0033333 = -0,0733838
    assert bt.bond_return(4.0, 5.0) == pytest.approx(-0.0733837842, abs=1e-9)


def test_bond_negative_rates():
    # tasso fermo a -0,5%: il titolo resta alla pari (c/y = 1), rendimento = c/12 = -0,005/12
    assert bt.bond_return(-0.5, -0.5) == pytest.approx(-0.005 / 12, abs=1e-12)
    # da -0,5% a -0,2%: c = -0,005, y = -0,002, n = 9,9166667
    # 0,998^-9,9166667 = e^(9,9166667 * 0,002002003) = e^0,0198532 = 1,0200516
    # prezzo = 2,5 * (1 - 1,0200516) + 1,0200516 = -0,0501290 + 1,0200516 = 0,9699226
    # rendimento = 0,9699226 - 1 - 0,005/12 = -0,0300774 - 0,0004167 = -0,0304941 (circa -0,0304940)
    assert bt.bond_return(-0.5, -0.2) == pytest.approx(-0.0304940, abs=1e-6)


def test_bond_rate_near_zero():
    # |y| < 1e-9: prezzo = c*n + 1
    # c = 0,01, y = 0: prezzo = 0,01 * 9,91667 + 1 = 1,0991667
    # rendimento = 0,0991667 + 0,01/12 = 0,0991667 + 0,0008333 = 0,1 esatto
    assert bt.bond_return(1.0, 0.0) == pytest.approx(0.1, abs=1e-12)
    assert bt.bond_return(0.0, 0.0) == pytest.approx(0.0, abs=1e-12)
    # 1e-10 è "vicino a zero": stessa formula, niente divisione per quasi zero
    assert bt.bond_return(1.0, 1e-8) == pytest.approx(0.1, abs=1e-12)


def test_cash_uses_previous_month_rate():
    # euribor: gennaio 1,2%, febbraio 6,0% -> rendimento di febbraio = 1,2/100/12 = 0,001
    t = _fake_table("2020-01", "2020-02")
    t["euribor3m_pct"] = [1.2, 6.0]
    r = bt.monthly_returns(t)
    assert r.at["2020-02", "cash"] == pytest.approx(0.001)
    assert math.isnan(r.at["2020-01", "cash"])


def test_returns_are_in_euro():
    # S&P da 100 a 110 dollari, cambio da 1,0 a 1,1 dollari per euro:
    # in euro da 100 a 100 -> rendimento 0
    t = _fake_table("2020-01", "2020-02")
    t["spx_usd"] = [100.0, 110.0]
    t["usd_per_eur"] = [1.0, 1.1]
    t["spx_eur"] = t["spx_usd"] / t["usd_per_eur"]
    assert bt.monthly_returns(t).at["2020-02", "spx"] == pytest.approx(0.0, abs=1e-12)


def test_estimated_dividends_add_one_twelfth():
    t = _fake_table("2020-01", "2020-03")
    r = bt.monthly_returns(t)
    rd = bt.monthly_returns(t, dividends=True)
    assert rd.at["2020-02", "spx"] - r.at["2020-02", "spx"] == pytest.approx(0.016 / 12)
    assert rd.at["2020-02", "sx5e"] - r.at["2020-02", "sx5e"] == pytest.approx(0.028 / 12)
    assert rd.at["2020-02", "gold"] == r.at["2020-02", "gold"]


# ------------------------------------------------------------------ §6 simulazione

def test_still_position_only_costs_and_stamp_duty():
    # S&P 500 fermo per 3 mesi.
    # ogni mese: h * 0,998^(1/12) * (1 - 0,002/12) = h * 0,99983322 * 0,99983333
    # dopo 3 mesi: h = 9990,00999 * 0,998^0,25 * 0,99983333^3
    #            = 9990,00999 * 0,99949962 * 0,99950008 = 9980,0199 (circa)
    # B = 9990,00999 * 0,99950008 = 9985,0158: h < B, quindi nessuna tassa
    # vendita finale: netto = h * 0,999 = 9970,04 (circa)
    months = bt.months_between("2020-01", "2020-04")
    r = _returns(months)
    res = bt.simulate(r, {"spx": 1.0}, "2020-01", "2020-04", K)
    h = H0 * 0.998 ** 0.25 * (1 - 0.002 / 12) ** 3
    assert res.values[0] == K
    assert res.values[-1] == pytest.approx(h)
    assert res.values[-1] == pytest.approx(9980.02, abs=0.01)
    assert res.final_net == pytest.approx(h * 0.999)
    assert res.final_net == pytest.approx(9970.04, abs=0.01)


def _one_month_sale(asset, r):
    months = ["2020-01", "2020-02"]
    rets = _returns(months, **{asset: [0.0, r]})
    return bt.simulate(rets, {asset: 1.0}, "2020-01", "2020-02", K)


def test_tax_26_percent_on_gain():
    # S&P +10% in un mese:
    # h = 9990,00999 * 1,1 * 0,998^(1/12) * (1 - 0,002/12)
    # B = 9990,00999 * (1 - 0,002/12)
    # netto = h - 0,26 * (h - B) - 0,001 * h
    s = 1 - 0.002 / 12
    h = H0 * 1.1 * 0.998 ** (1 / 12) * s
    B = H0 * s
    assert _one_month_sale("spx", 0.10).final_net == pytest.approx(h - 0.26 * (h - B) - 0.001 * h)


def test_tax_12_5_percent_on_bonds():
    # come sopra, ma TER 0,15% e aliquota 12,5%
    s = 1 - 0.002 / 12
    h = H0 * 1.1 * 0.9985 ** (1 / 12) * s
    B = H0 * s
    assert _one_month_sale("bond", 0.10).final_net == pytest.approx(h - 0.125 * (h - B) - 0.001 * h)


def test_no_tax_on_losses():
    # -10%: h < B, nessuna tassa, solo il costo di vendita
    s = 1 - 0.002 / 12
    h = H0 * 0.9 * 0.998 ** (1 / 12) * s
    assert _one_month_sale("spx", -0.10).final_net == pytest.approx(h * 0.999)


def test_rebalance_two_positions(monkeypatch):
    # Per avere numeri tondi: TER e bollo a zero (solo in questo test).
    monkeypatch.setitem(bt.TER, "spx", 0.0)
    monkeypatch.setitem(bt.TER, "gold", 0.0)
    monkeypatch.setattr(bt, "STAMP_DUTY", 0.0)
    # 50% S&P, 50% oro. Acquisto a novembre: 4995,004995 ciascuno.
    # Dicembre: S&P +20% -> 5994,005994; oro fermo -> 4995,004995. V = 10989,010989
    # obiettivo 5494,505495 ciascuno. Vendita S&P s = 499,500499
    # guadagno = s * (1 - 4995,004995/5994,005994) = s / 6 = 83,250083; tassa 26% = 21,645022
    # costo = 0,499500; incasso = 499,500499 - 21,645022 - 0,499500 = 477,355977
    # B S&P = 4995,004995 * (1 - 1/12) = 4578,754579; h S&P = 5494,505495
    # acquisto oro = 477,355977 / 1,001 = 476,879098 -> h oro = B oro = 5471,884093
    # Gennaio fermo: V = 10966,389588.
    # Vendita finale: tassa S&P = 0,26 * (5494,505495 - 4578,754579) = 238,095238
    # costo = 0,001 * 10966,389588 = 10,966390; netto = 10717,327960
    months = ["2020-11", "2020-12", "2021-01"]
    rets = _returns(months, spx=[0.0, 0.2, 0.0])
    res = bt.simulate(rets, {"spx": 0.5, "gold": 0.5}, "2020-11", "2021-01", K)
    assert res.values[2] == pytest.approx(10966.389588, abs=1e-5)
    assert res.final_net == pytest.approx(10717.327960, abs=1e-5)

    # senza ribilanciamento: V resta 10989,010989
    res_no = bt.simulate(rets, {"spx": 0.5, "gold": 0.5}, "2020-11", "2021-01", K,
                         rebalance=False)
    assert res_no.values[2] == pytest.approx(10989.010989, abs=1e-5)


def test_no_rebalance_in_last_month(monkeypatch):
    monkeypatch.setattr(bt, "STAMP_DUTY", 0.0)
    monkeypatch.setitem(bt.TER, "spx", 0.0)
    monkeypatch.setitem(bt.TER, "gold", 0.0)
    # fine a dicembre: niente ribilanciamento, V = 5994,005994 + 4995,004995
    months = ["2020-11", "2020-12"]
    rets = _returns(months, spx=[0.0, 0.2])
    res = bt.simulate(rets, {"spx": 0.5, "gold": 0.5}, "2020-11", "2020-12", K)
    assert res.values[1] == pytest.approx(10989.010989, abs=1e-5)


def test_monthly_contributions(monkeypatch):
    monkeypatch.setattr(bt, "STAMP_DUTY", 0.0)
    # Liquidità a tasso zero (TER 0). 10 000 all'inizio, 200 alla fine di febbraio e di marzo.
    # gennaio: 9990,00999; febbraio: + 200/1,001 = 199,80020 -> 10189,81019
    # marzo: + 199,80020 -> 10389,61039; versato 10 400
    # vendita: nessun guadagno, costo 10,38961 -> netto 10379,22078
    # momento peggiore: V / versato - 1 = 1/1,001 - 1 = -0,000999 (uguale a febbraio e marzo)
    months = ["2020-01", "2020-02", "2020-03"]
    rets = _returns(months)
    m = bt.contribution_measures(rets, {"cash": 1.0}, "2020-01", "2020-03", K, monthly=200.0)
    assert m["total_contributed"] == 10_400.0
    assert m["final_net"] == pytest.approx(10379.22078, abs=1e-5)
    assert m["worst_vs_contributed"] == pytest.approx(1 / 1.001 - 1)
    assert m["worst_month"] == "2020-02"


# ------------------------------------------------------------------ §7 misure

def test_max_drawdown_known_series():
    # massimi 110 e 120; minimi 88 (-20%) e 90 (-25%): caduta massima 25%
    assert bt.max_drawdown([100, 110, 99, 88, 110, 120, 90]) == pytest.approx(0.25)
    assert bt.max_drawdown([100, 101, 102]) == 0.0


def test_calendar_years_known_series():
    # 2020: 120/100 - 1 = +20%; 2021: 108/120 - 1 = -10% (giugno non conta)
    years = bt.calendar_year_returns(["2019-12", "2020-12", "2021-06", "2021-12"],
                                     [100, 120, 90, 108])
    assert years == {2020: pytest.approx(0.2), 2021: pytest.approx(-0.1)}


def test_underwater_known_series():
    # massimo 110 al mese 1, si torna a 110 al mese 4: 3 mesi
    # massimo 120 al mese 5, 90 al mese 6 e fine: 1 mese, non recuperata
    u = bt.underwater_periods([100, 110, 99, 88, 110, 120, 90])
    assert u == [
        {"peak": 1, "end": 4, "months": 3, "recovered": True},
        {"peak": 5, "end": 6, "months": 1, "recovered": False},
    ]
    # 60 mesi esatti sotto il massimo
    u60 = bt.underwater_periods([100] + [90] * 59 + [100])
    assert u60 == [{"peak": 0, "end": 60, "months": 60, "recovered": True}]


def test_annual_growth():
    # 10 000 -> 12 100 in 24 mesi: (1,21)^(12/24) - 1 = 1,1 - 1 = 10%
    assert bt.annual_growth(12_100, 10_000, 24) == pytest.approx(0.10)


def test_number_of_windows_and_steps():
    t = _fake_table()
    r = bt.monthly_returns(t)
    assert len(bt.window_finals(r, bt.PORTFOLIOS["A"], *bt.PERIOD_LONG)) == 204
    assert len(bt.window_finals(r, bt.PORTFOLIOS["D"], *bt.PERIOD_SHORT)) == 48
    assert bt.simulate(r, bt.PORTFOLIOS["A"], *bt.PERIOD_LONG).steps == 263
    assert bt.simulate(r, bt.PORTFOLIOS["D"], *bt.PERIOD_SHORT).steps == 107


# ------------------------------------------------------------------ cassaforte e futuro

def test_vault_is_blocked():
    t = _fake_table("2022-10", "2023-02")
    with pytest.raises(bt.VaultError):
        bt.monthly_returns(t)
    r = bt.monthly_returns(t, allow_vault=True)
    with pytest.raises(bt.VaultError):
        bt.simulate(r, bt.PORTFOLIOS["A"], "2022-10", "2023-01")
    # solo con il parametro esplicito (che in questa fase non si usa mai)
    bt.simulate(r, bt.PORTFOLIOS["A"], "2022-10", "2023-01", allow_vault=True)


def test_future_price_does_not_change_the_past():
    # cambio i prezzi del mese m+1 = 2005-07: niente deve cambiare fino al mese m = 2005-06
    t1 = _fake_table()
    t2 = t1.copy()
    i = t2.index[t2["month"] == "2005-07"][0]
    for col in ["spx_eur", "sx5e_eur", "gold_eur", "btc_eur"]:
        t2.loc[i, col] *= 1.5
    t2.loc[i, "y10_pct"] += 2
    t2.loc[i, "euribor3m_pct"] += 2
    r1, r2 = bt.monthly_returns(t1), bt.monthly_returns(t2)
    pd.testing.assert_frame_equal(r1.loc[:"2005-06"], r2.loc[:"2005-06"])
    for name in ["A", "B", "C", "D-core"]:
        a = bt.simulate(r1, bt.PORTFOLIOS[name], "2001-01", "2010-12")
        b = bt.simulate(r2, bt.PORTFOLIOS[name], "2001-01", "2010-12")
        k = a.months.index("2005-06")
        assert a.values[: k + 1] == b.values[: k + 1]
        assert a.values[k + 1] != b.values[k + 1]


def test_missing_return_stops_simulation():
    months = ["2020-01", "2020-02"]
    rets = _returns(months, spx=[0.0, math.nan])
    with pytest.raises(ValueError, match="mancante"):
        bt.simulate(rets, {"spx": 1.0}, "2020-01", "2020-02")


# ------------------------------------------------------------------ §8 e tutte le misure

def _ev(growth, dd, passes=True):
    return {"annual_growth": growth, "max_drawdown": dd, "passes_all": passes}


def test_pick_winner_rules():
    # più guadagno vince se la distanza è almeno 0,50 punti
    assert bt.pick_winner({"A": _ev(0.060, 0.30), "B": _ev(0.050, 0.10)}) == "A"
    # meno di 0,50 punti: vince la caduta più piccola
    assert bt.pick_winner({"A": _ev(0.060, 0.30), "B": _ev(0.0559, 0.10)}) == "B"
    # chi non passa non può vincere; nessuno passa -> nessun vincitore
    assert bt.pick_winner({"A": _ev(0.09, 0.1, False), "B": _ev(0.05, 0.1)}) == "B"
    assert bt.pick_winner({"A": _ev(0.09, 0.1, False)}) is None


def test_all_measures_on_invented_prices():
    m = bt.all_measures(_fake_table())
    long_p = m["periods"]["long"]["portfolios"]
    short_p = m["periods"]["short"]["portfolios"]
    assert set(long_p) == {"A", "B", "C", "LIQ", "D-core"}
    assert set(short_p) == {"A", "B", "C", "D", "LIQ"}
    assert long_p["A"]["evaluation"]["steps"] == 263
    assert long_p["A"]["evaluation"]["windows"] == 204
    assert short_p["D"]["evaluation"]["windows"] == 48
    assert long_p["A"]["monthly_contributions"]["total_contributed"] == 10_000 + 200 * 263
    assert set(m["verdict"]) == {"winner_A_B_C_long", "D_passes_short", "final_winner", "note"}
    # stesso input, stesso output
    assert bt.all_measures(_fake_table()) == m


# ------------------------------------------------------------------ revisione esterna

def test_rebalance_buys_in_proportion_three_positions(monkeypatch):
    # TER e bollo a zero (solo in questo test). Pesi: S&P 0,5, oro 0,3, obbligazioni 0,2.
    for a in ("spx", "gold", "bond"):
        monkeypatch.setitem(bt.TER, a, 0.0)
    monkeypatch.setattr(bt, "STAMP_DUTY", 0.0)
    # Acquisto a novembre (K / 1,001): S&P 4995,004995, oro 2997,002997, obbl. 1998,001998
    # Dicembre: S&P +30% -> 6493,506494; oro -10% -> 2697,302697; obbl. +5% -> 2097,902098
    # V = 11288,711289; obiettivi 5644,355645 / 3386,613387 / 2257,742258
    # vendita S&P s = 849,150849; guadagno = s * (1 - 1/1,3) = 195,957888; tassa 26% = 50,949051
    # costo 0,849151; incasso = 797,352647; da comprare 797,352647 / 1,001 = 796,556091
    # mancano: oro 689,310690, obbl. 159,840160 (totale 849,150849)
    # oro compra 796,556091 * 689,310690 / 849,150849 = 646,616121 -> h oro 3343,918818
    # obbl. compra 796,556091 * 159,840160 / 849,150849 = 149,939970 -> h obbl. 2247,842068
    # V dopo il ribilanciamento = 5644,355644 + 3343,918818 + 2247,842068 = 11236,116531
    # (controllo: 11288,711289 - 50,949051 - 0,849151 - 0,796556 = 11236,116531)
    # Gennaio: oro +10% -> 3343,918818 * 1,1 = 3678,310700 (S&P e obbligazioni ferme)
    # V gennaio = 5644,355644 + 3678,310700 + 2247,842068 = 11570,508413
    # Se gli acquisti fossero divisi in un altro modo, h oro e quindi V gennaio cambierebbero.
    # Vendita finale:
    #   S&P: B = 4995,004995 * (1 - 849,150849/6493,506494) = 4341,812030; guadagno 1302,543614
    #        tassa 26% = 338,661339
    #   oro: B = 2997,002997 + 646,616121 = 3643,619118; guadagno 3678,310700 - 3643,619118
    #        = 34,691582; tassa 26% = 9,019811
    #   obbl.: B = 1998,001998 + 149,939970 = 2147,941968; guadagno 99,900100; tassa 12,5% = 12,487512
    #   costo 0,001 * 11570,508413 = 11,570508
    #   netto = 11570,508413 - 338,661339 - 9,019811 - 12,487512 - 11,570508 = 11198,769243
    #   (con tutte le cifre: 11198,769242)
    months = ["2020-11", "2020-12", "2021-01"]
    rets = _returns(months, spx=[0.0, 0.30, 0.0], gold=[0.0, -0.10, 0.10], bond=[0.0, 0.05, 0.0])
    res = bt.simulate(rets, {"spx": 0.5, "gold": 0.3, "bond": 0.2}, "2020-11", "2021-01", K)
    assert res.values[2] == pytest.approx(11570.508413, abs=1e-5)
    assert res.final_net == pytest.approx(11198.769242, abs=1e-5)


def _criteria(dd=0.1, years=None, under=None, growth=0.05, liq=0.01, finals=None):
    return bt.check_criteria(
        dd, years if years is not None else {2020: 0.0}, under or [], growth, liq,
        finals if finals is not None else [K + 1] * 10, K,
    )


def test_criterion_1_max_drawdown_at_limit():
    assert _criteria(dd=0.25)["1_max_drawdown"] is True
    assert _criteria(dd=0.25 + 1e-12)["1_max_drawdown"] is False


def test_criterion_2_calendar_years_at_limit():
    assert _criteria(years={2020: -0.20, 2021: 0.3})["2_calendar_years"] is True
    assert _criteria(years={2020: -0.20 - 1e-12})["2_calendar_years"] is False


def test_criterion_3_underwater_at_limit():
    ok = [{"months": 60, "recovered": True}, {"months": 60, "recovered": False}]
    assert _criteria(under=ok)["3_underwater"] is True
    assert _criteria(under=[{"months": 61, "recovered": True}])["3_underwater"] is False
    assert _criteria(under=[{"months": 61, "recovered": False}])["3_underwater"] is False


def test_criterion_4_must_be_strictly_higher_than_liq():
    assert _criteria(growth=0.03, liq=0.03)["4_beats_liq"] is False
    assert _criteria(growth=0.03 + 1e-12, liq=0.03)["4_beats_liq"] is True


def test_criterion_5_windows_at_limit():
    # 9 finestre su 10 sopra K = 0,90: passa; 8 su 10: no
    assert _criteria(finals=[K + 1] * 9 + [K - 1])["5_windows"] is True
    assert _criteria(finals=[K + 1] * 8 + [K - 1] * 2)["5_windows"] is False
    # esattamente K non è "sopra K": 9 su 10 pari a K -> 0,10 -> non passa
    assert _criteria(finals=[K] * 9 + [K + 1])["5_windows"] is False
    assert _criteria(finals=[])["5_windows"] is False


def _v(growth, dd, passes=True):
    return {"annual_growth": growth, "max_drawdown": dd, "passes_all": passes}


def test_verdict_d_fails():
    long_ev = {"A": _v(0.07, 0.30), "B": _v(0.05, 0.20), "C": _v(0.04, 0.10, False)}
    short_ev = {"A": _v(0.10, 0.2), "B": _v(0.08, 0.1), "C": _v(0.05, 0.1), "D": _v(0.20, 0.1, False)}
    v = bt.verdict(long_ev, short_ev)
    assert v["winner_A_B_C_long"] == "A"
    assert v["D_passes_short"] is False
    assert v["final_winner"] == "A"


def test_verdict_none_of_a_b_c_passes_and_d_passes():
    long_ev = {n: _v(0.05, 0.3, False) for n in ("A", "B", "C")}
    short_ev = {"A": _v(0.1, 0.1), "B": _v(0.1, 0.1), "C": _v(0.1, 0.1), "D": _v(0.03, 0.1)}
    v = bt.verdict(long_ev, short_ev)
    assert v["winner_A_B_C_long"] is None
    assert v["final_winner"] == "D"


def test_verdict_nobody_passes():
    long_ev = {n: _v(0.05, 0.3, False) for n in ("A", "B", "C")}
    short_ev = {"A": _v(0.1, 0.1), "B": _v(0.1, 0.1), "C": _v(0.1, 0.1), "D": _v(0.2, 0.1, False)}
    assert bt.verdict(long_ev, short_ev)["final_winner"] is None


def test_verdict_d_passes_and_is_compared_with_winner():
    long_ev = {"A": _v(0.070, 0.30), "B": _v(0.050, 0.20), "C": _v(0.040, 0.10)}
    # D guadagna 0,8 punti più di A sul 2014-2022 (sopra 0,5): vince D
    short = {"A": _v(0.060, 0.15, False), "B": _v(0.0, 0.1), "C": _v(0.0, 0.1), "D": _v(0.068, 0.25)}
    assert bt.verdict(long_ev, short)["final_winner"] == "D"
    # D guadagna 0,3 punti più di A (sotto 0,5): vince la caduta più piccola, cioè A
    # (A su questo periodo non passa tutti i criteri: si confronta lo stesso, spec §12)
    short["D"] = _v(0.063, 0.25)
    assert bt.verdict(long_ev, short)["final_winner"] == "A"
    # stessa distanza, ma D ha la caduta più piccola: vince D
    short["D"] = _v(0.063, 0.10)
    assert bt.verdict(long_ev, short)["final_winner"] == "D"
    # A guadagna 0,7 punti più di D: vince A
    short["D"] = _v(0.053, 0.05)
    assert bt.verdict(long_ev, short)["final_winner"] == "A"


def test_all_measures_returns_plain_python_types():
    m = bt.all_measures(_fake_table("2010-01", "2016-12"),
                        period_long=("2010-01", "2016-12"), period_short=("2014-01", "2016-12"))
    json.dumps(m)  # nessun tipo numpy

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                assert type(k) in (str, int)
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        else:
            assert o is None or type(o) in (str, int, float, bool), type(o)
    walk(m)


def test_simulate_rejects_bad_ranges_and_returns():
    months = ["2020-01", "2020-02", "2020-03"]
    rets = _returns(months)
    with pytest.raises(ValueError):
        bt.simulate(rets, {"spx": 1.0}, "2020-02", "2020-02")      # start == end
    with pytest.raises(ValueError):
        bt.simulate(rets, {"spx": 1.0}, "2020-03", "2020-02")      # start dopo end
    with pytest.raises(ValueError):
        bt.simulate(rets, {"spx": 1.0}, "2019-12", "2020-02")      # start fuori indice
    for bad in (-1.0, -1.5, math.inf):
        r = _returns(months, spx=[0.0, bad, 0.0])
        with pytest.raises(ValueError, match="non valido"):
            bt.simulate(r, {"spx": 1.0}, "2020-01", "2020-03")
    # un rendimento non valido di una posizione con peso zero non conta
    r = _returns(months, btc=[0.0, math.nan, 0.0])
    bt.simulate(r, {"spx": 1.0}, "2020-01", "2020-03")


def test_monthly_returns_rejects_bad_month_order():
    t = _fake_table("2020-01", "2020-04")
    with pytest.raises(ValueError, match="consecutivi"):
        bt.monthly_returns(t.iloc[[0, 2, 3]])           # manca un mese
    with pytest.raises(ValueError, match="consecutivi"):
        bt.monthly_returns(t.iloc[[1, 0, 2, 3]])        # fuori ordine
    with pytest.raises(ValueError, match="consecutivi"):
        bt.monthly_returns(pd.concat([t, t.iloc[[3]]]))  # doppione


def test_load_monthly_table_checks_sha256_and_keeps_digits(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("month,spx_eur\n2020-01,0.30000000000000004\n2020-02,1074.7785356398285\n",
                 encoding="utf-8")
    t = bt.load_monthly_table(p, sha256_file(p))
    assert t["spx_eur"].iloc[0] == 0.30000000000000004
    assert t["spx_eur"].iloc[1] == 1074.7785356398285
    assert t["month"].iloc[0] == "2020-01"
    with pytest.raises(ValueError, match="SHA-256"):
        bt.load_monthly_table(p, "0" * 64)


# ------------------------------------------------------------------ §13 prudenza

def _full_ev(passes=True, dd=0.10, worst=-0.05, longest=20, growth=0.06, liq=0.01, share=1.0):
    """Valutazione inventata, lontana da tutte le fasce 'al limite' salvo dove indicato."""
    return {"passes_all": passes, "max_drawdown": dd, "worst_year": worst,
            "longest_underwater_months": longest, "annual_growth": growth,
            "liq_annual_growth": liq, "windows_share": share}


@pytest.mark.parametrize("field,value,criterion", [
    ("dd", 0.22, "1_max_drawdown"), ("dd", 0.28, "1_max_drawdown"),
    ("worst", -0.22, "2_calendar_years"), ("worst", -0.18, "2_calendar_years"),
    ("longest", 54, "3_underwater"), ("longest", 66, "3_underwater"),
    ("share", 0.87, "5_windows"), ("share", 0.93, "5_windows"),
])
def test_borderline_bands_include_both_ends(field, value, criterion):
    flags = bt.borderline_flags(_full_ev(**{field: value}))
    assert flags[criterion] is True
    assert sum(flags.values()) == 1


@pytest.mark.parametrize("field,value", [
    ("dd", 0.2199), ("dd", 0.2801), ("worst", -0.2201), ("worst", -0.1799),
    ("longest", 53), ("longest", 67), ("share", 0.8699), ("share", 0.9301),
])
def test_borderline_bands_outside(field, value):
    assert not any(bt.borderline_flags(_full_ev(**{field: value})).values())


def test_borderline_growth_vs_liq():
    # differenza +0,005 e -0,005 comprese; 0,0051 no (0,0051 per evitare l'arrotondamento)
    assert bt.borderline_flags(_full_ev(growth=0.015, liq=0.01))["4_beats_liq"] is True
    assert bt.borderline_flags(_full_ev(growth=0.005, liq=0.01))["4_beats_liq"] is True
    assert bt.borderline_flags(_full_ev(growth=0.0151, liq=0.01))["4_beats_liq"] is False
    # nessuna finestra (quota NaN) non è "al limite"
    assert bt.borderline_flags(_full_ev(share=math.nan))["5_windows"] is False


def test_portfolio_status():
    assert bt.portfolio_status(_full_ev()) == "netto"
    assert bt.portfolio_status(_full_ev(dd=0.24)) == "al limite"
    assert bt.portfolio_status(_full_ev(passes=False)) == "non passa"


def test_clear_beats_borderline_even_with_less_growth():
    # A al limite con molto più guadagno; B netto: vince B, netto
    c = {"A": _full_ev(growth=0.09, dd=0.24), "B": _full_ev(growth=0.05), "C": _full_ev(passes=False)}
    assert bt.pick_winner_prudent(c) == ("B", "netto")
    # tutti al limite: vale la regola del §8 tra loro, il vincitore porta lo stato
    c = {"A": _full_ev(growth=0.09, dd=0.24), "B": _full_ev(growth=0.05, dd=0.23)}
    assert bt.pick_winner_prudent(c) == ("A", "al limite")
    # due netti a meno di 0,5 punti: vince la caduta più piccola
    c = {"A": _full_ev(growth=0.060, dd=0.15), "B": _full_ev(growth=0.057, dd=0.12)}
    assert bt.pick_winner_prudent(c) == ("B", "netto")
    assert bt.pick_winner_prudent({"A": _full_ev(passes=False)}) == (None, None)


def _long(a=None, b=None, c=None, dcore=None):
    return {"A": a or _full_ev(growth=0.07), "B": b or _full_ev(growth=0.05),
            "C": c or _full_ev(growth=0.04), "D-core": dcore or _full_ev()}


def _short(a=None, d=None, dcore=None):
    return {"A": a or _full_ev(growth=0.06), "B": _full_ev(growth=0.04),
            "C": _full_ev(growth=0.03), "D": d or _full_ev(growth=0.09),
            "D-core": dcore or _full_ev(growth=0.07)}


def test_prudent_d_cannot_win_if_d_core_fails_2008():
    v = bt.prudent_verdict(_long(dcore=_full_ev(passes=False)), _short())
    assert v["D_passes_short"] is True
    assert v["D_core_passes_long"] is False
    assert v["D_eligible"] is False
    assert (v["winner"], v["status"]) == ("A", "netto")


def test_prudent_d_wins_when_eligible_and_clearly_better():
    v = bt.prudent_verdict(_long(), _short())
    assert v["D_eligible"] is True
    # D 9% contro A 6% sul 2014-2022: +3 punti, vince D
    assert (v["winner"], v["status"]) == ("D", "netto")
    # contributo del Bitcoin = 0,09 - 0,07 = 0,02
    assert v["bitcoin_contribution"] == pytest.approx(0.02)


def test_prudent_d_fails_short():
    v = bt.prudent_verdict(_long(), _short(d=_full_ev(passes=False)))
    assert v["D_eligible"] is False
    assert (v["winner"], v["status"]) == ("A", "netto")


def test_prudent_no_a_b_c_and_d_eligible():
    fail = _full_ev(passes=False)
    v = bt.prudent_verdict(_long(a=fail, b=fail, c=fail), _short(d=_full_ev(dd=0.25)))
    assert v["winner_A_B_C_long"] is None
    assert (v["winner"], v["status"]) == ("D", "al limite")


def test_prudent_clear_beats_borderline_in_step_2():
    # A netto sul periodo lungo, D al limite con più guadagno: resta A
    v = bt.prudent_verdict(_long(), _short(d=_full_ev(growth=0.12, dd=0.27)))
    assert (v["winner"], v["status"]) == ("A", "netto")
    # A al limite sul periodo lungo, D netto con meno guadagno: vince D
    v = bt.prudent_verdict(_long(a=_full_ev(growth=0.07, dd=0.26), b=_full_ev(passes=False),
                                 c=_full_ev(passes=False)),
                           _short(d=_full_ev(growth=0.02)))
    assert v["winner_A_B_C_long_status"] == "al limite"
    assert (v["winner"], v["status"]) == ("D", "netto")


def test_prudent_same_status_uses_half_point_rule():
    # A e D netti; D +0,3 punti (sotto 0,5) e caduta più grande: vince A
    v = bt.prudent_verdict(_long(), _short(a=_full_ev(growth=0.060, dd=0.10),
                                           d=_full_ev(growth=0.063, dd=0.15)))
    assert (v["winner"], v["status"]) == ("A", "netto")


def _pv(winner, status):
    return {"winner": winner, "status": status}


def test_combine_versions_all_branches():
    r = bt.combine_versions(_pv("B", "netto"), _pv("B", "netto"))
    assert (r["final_winner"], r["final_status"], r["versions_agree"]) == ("B", "netto", True)
    assert "al limite" not in r["sentence"]

    r = bt.combine_versions(_pv("B", "netto"), _pv("B", "al limite"))
    assert (r["final_winner"], r["final_status"]) == ("B", "al limite")
    assert "al limite" in r["sentence"]

    r = bt.combine_versions(_pv("B", "netto"), _pv("C", "netto"))
    assert (r["final_winner"], r["final_status"], r["versions_agree"]) == (None, "al limite", False)
    assert "al limite" in r["sentence"] and "B" in r["sentence"] and "C" in r["sentence"]

    r = bt.combine_versions(_pv(None, None), _pv("C", "netto"))
    assert (r["final_winner"], r["final_status"]) == (None, "al limite")
    assert "al limite" in r["sentence"]

    r = bt.combine_versions(_pv(None, None), _pv(None, None))
    assert (r["final_winner"], r["final_status"]) == (None, "nessuno")

    r = bt.combine_versions(_pv("D", "netto"), _pv("D", "netto"))
    assert "2008" in r["sentence"]


def test_all_measures_has_prudence_outputs():
    m = bt.all_measures(_fake_table())
    pr = m["prudence"]
    assert set(pr["versions"]) == {"prices", "dividends"}
    for v in pr["versions"].values():
        assert set(v["long"]["portfolios"]) == set(bt.PRUDENT_LONG)
        assert set(v["short"]["portfolios"]) == set(bt.PRUDENT_SHORT)
        assert v["short"]["portfolios"]["D-core"]["evaluation"]["windows"] == 48
        assert v["verdict"]["bitcoin_contribution"] == pytest.approx(
            v["short"]["portfolios"]["D"]["evaluation"]["annual_growth"]
            - v["short"]["portfolios"]["D-core"]["evaluation"]["annual_growth"])
    # la versione solo prezzi riusa le stesse valutazioni delle uscite di sempre
    assert (pr["versions"]["prices"]["long"]["portfolios"]["A"]["evaluation"]
            == m["periods"]["long"]["portfolios"]["A"]["evaluation"])
    # la versione con dividendi ha davvero rendimenti diversi
    assert (pr["versions"]["dividends"]["long"]["portfolios"]["A"]["evaluation"]["final_net"]
            > pr["versions"]["prices"]["long"]["portfolios"]["A"]["evaluation"]["final_net"])
    assert set(pr["final"]) >= {"final_winner", "final_status", "sentence", "versions_agree"}
    assert "verdict" in m  # l'uscita di prima resta


# ------------------------------------------------------------------ aggiunte della revisione esterna

def test_still_position_12_months_each_asset():
    # 12 mesi fermi, un'attività al 100%: h = H0 * (1 - TER) * (1 - 0,002/12)^12
    # H0 = 9990,009990; (1 - 0,002/12)^12 = 0,998001832315
    # h < B (B = H0 * 0,998001832315): nessuna tassa, netto = h * 0,999
    expected = {
        "spx": 9950.108178, "sx5e": 9950.108178, "bond": 9955.093202,
        "gold": 9945.123154, "btc": 9870.347792, "cash": 9970.048275,
    }
    months = bt.months_between("2021-01", "2022-01")
    r = _returns(months)
    for asset, v12 in expected.items():
        res = bt.simulate(r, {asset: 1.0}, "2021-01", "2022-01", K)
        assert res.values[-1] == pytest.approx(v12, abs=1e-6), asset
        assert res.final_net == pytest.approx(v12 * 0.999, abs=1e-6), asset


def test_rebalance_sale_at_a_loss_pays_no_tax(monkeypatch):
    monkeypatch.setitem(bt.TER, "spx", 0.0)
    monkeypatch.setitem(bt.TER, "gold", 0.0)
    monkeypatch.setattr(bt, "STAMP_DUTY", 0.0)
    # 50% S&P, 50% oro, acquisto a novembre: 4995,004995 ciascuno.
    # dicembre: S&P -10% -> 4495,504496; oro -30% -> 3496,503497; V = 7992,007992; obiettivo 3996,003996
    # vendita S&P s = 499,500500; guadagno = s * (1 - 4995,004995/4495,504496) = -s/9 = -55,500056 -> tassa 0
    # incasso = 499,500500 - 0 - 0,499500 = 499,000999; acquisto oro = 499,000999 / 1,001 = 498,502497
    # V = 3996,003996 + 3496,503497 + 498,502497 = 7991,009989 (gennaio fermo: uguale)
    # vendita finale: tutte e due sotto il costo fiscale, nessuna tassa: 7991,009989 * 0,999 = 7983,018979
    months = ["2020-11", "2020-12", "2021-01"]
    rets = _returns(months, spx=[0.0, -0.10, 0.0], gold=[0.0, -0.30, 0.0])
    res = bt.simulate(rets, {"spx": 0.5, "gold": 0.5}, "2020-11", "2021-01", K)
    assert res.values[2] == pytest.approx(7991.009989, abs=1e-5)
    assert res.final_net == pytest.approx(7983.018979, abs=1e-5)


def test_rebalance_three_positions_buys_in_proportion_to_gaps(monkeypatch):
    for a in ("spx", "sx5e", "gold"):
        monkeypatch.setitem(bt.TER, a, 0.0)
    monkeypatch.setattr(bt, "STAMP_DUTY", 0.0)
    # pesi 50/25/25; acquisto 4995,004995 / 2497,502498 / 2497,502498
    # dicembre: S&P +20% -> 5994,005994; Stoxx fermo 2497,502498; oro -20% -> 1998,001998; V = 10489,510490
    # obiettivi, su V prima delle vendite: 5244,755245 / 2622,377622 / 2622,377622
    # vendita S&P s = 749,250749; guadagno s/6 = 124,875125; tassa 32,467532; costo 0,749251
    # incasso 716,033966; da comprare 716,033966 / 1,001 = 715,318647
    # mancano: Stoxx 124,875125 (1/6), oro 624,375624 (5/6) -> +119,219775 e +596,098873
    # V dicembre = 5244,755245 + 2616,722272 + 2594,100871 = 10455,578388
    # gennaio, oro +10%: V = 5244,755245 + 2616,722272 + 2853,510958 = 10714,988475
    # vendita finale: tassa S&P 0,26 * (5244,755245 - 4370,629371) = 227,272727; costo 10,714988
    # netto = 10714,988475 - 227,272727 - 10,714988 = 10477,000759
    # (comprando 50/50 per peso: 10691,144520; con obiettivi ricalcolati dopo la vendita: 10726,910452)
    months = ["2020-11", "2020-12", "2021-01"]
    rets = _returns(months, spx=[0.0, 0.2, 0.0], gold=[0.0, -0.2, 0.1])
    res = bt.simulate(rets, {"spx": 0.5, "sx5e": 0.25, "gold": 0.25}, "2020-11", "2021-01", K)
    assert res.values[1] == pytest.approx(10455.578388, abs=1e-5)
    assert res.values[2] == pytest.approx(10714.988475, abs=1e-5)
    assert res.final_net == pytest.approx(10477.000759, abs=1e-5)


def test_contributions_come_after_december_rebalance(monkeypatch):
    monkeypatch.setitem(bt.TER, "spx", 0.0)
    monkeypatch.setitem(bt.TER, "gold", 0.0)
    monkeypatch.setattr(bt, "STAMP_DUTY", 0.0)
    # come test_rebalance_two_positions, più 200 € a fine dicembre e a fine gennaio (199,800200 investiti)
    # dicembre: prima il ribilanciamento (V = 10966,389588), poi +199,800200 -> 11166,189788
    # (versando prima del ribilanciamento verrebbe 11166,544270)
    # gennaio fermo: +199,800200 -> 11365,989987
    # vendita finale: tassa S&P 0,26 * 915,750916 = 238,095238 (il versamento alza h e B di pari importo)
    # netto = 11365,989987 - 238,095238 - 11,365990 = 11116,528759
    months = ["2020-11", "2020-12", "2021-01"]
    rets = _returns(months, spx=[0.0, 0.2, 0.0])
    w = {"spx": 0.5, "gold": 0.5}
    sim = bt.simulate(rets, w, "2020-11", "2021-01", K, monthly_contribution=200.0)
    assert sim.values[1] == pytest.approx(11166.189788, abs=1e-5)
    assert sim.values[2] == pytest.approx(11365.989987, abs=1e-5)
    m = bt.contribution_measures(rets, w, "2020-11", "2021-01", K, monthly=200.0)
    assert m["final_net"] == pytest.approx(11116.528759, abs=1e-5)
    assert m["total_contributed"] == 10_400.0


def test_bond_negative_rate():
    # c = 0,005, y = -0,005, n = 9,916667: 0,995^-9,916667 = 1,0509638
    # prezzo = c/y * (1 - 1,0509638) + 1,0509638 = 0,0509638 + 1,0509638 = 1,1019276
    # rendimento = 0,1019276 + 0,005/12 = 0,1023444  (con la formula "vicino a zero" verrebbe 0,05)
    assert bt.bond_return(0.5, -0.5) == pytest.approx(0.1023443896, abs=1e-9)


def test_gold_and_btc_returns_are_in_euro():
    # oro e Bitcoin fermi a 100 dollari, cambio da 1,00 a 1,25: in euro da 100 a 80 -> -20%
    t = _fake_table("2020-01", "2020-02")
    t["gold_usd"] = [100.0, 100.0]
    t["btc_usd"] = [100.0, 100.0]
    t["usd_per_eur"] = [1.0, 1.25]
    t["gold_eur"] = t["gold_usd"] / t["usd_per_eur"]
    t["btc_eur"] = t["btc_usd"] / t["usd_per_eur"]
    r = bt.monthly_returns(t)
    assert r.at["2020-02", "gold"] == pytest.approx(-0.20)
    assert r.at["2020-02", "btc"] == pytest.approx(-0.20)


def test_missing_return_of_unused_asset_is_ignored():
    # come nei dati veri: Bitcoin vuoto prima del 2014; A non ha Bitcoin e deve simulare normalmente
    months = ["2013-11", "2013-12", "2014-01"]
    rets = _returns(months, btc=[math.nan] * 3)
    res = bt.simulate(rets, bt.PORTFOLIOS["A"], "2013-11", "2014-01", K)
    assert len(res.values) == 3


def test_max_drawdown_and_underwater_count_v0():
    # V_0 = K è il massimo: caduta 1 - 90/100 = 10%; si torna a 100 al mese 3: 3 mesi sotto il massimo
    assert bt.max_drawdown([100, 90, 95, 100]) == pytest.approx(0.10)
    assert bt.underwater_periods([100, 90, 95, 100]) == [
        {"peak": 0, "end": 3, "months": 3, "recovered": True},
    ]


def test_each_window_is_a_fresh_60_month_simulation():
    r = bt.monthly_returns(_fake_table("2000-12", "2006-02"))
    w = bt.window_finals(r, bt.PORTFOLIOS["A"], "2001-01", "2006-02")
    assert [(x["start"], x["end"]) for x in w] == [("2001-01", "2006-01"), ("2001-02", "2006-02")]
    for x in w:
        # simulazione nuova, ribilanciamento a dicembre, vendita finale al mese s + 60
        assert x["final_net"] == bt.simulate(r, bt.PORTFOLIOS["A"], x["start"], x["end"]).final_net


def _evaluate_with(monkeypatch, months, values, final_net, window_nets, liq_growth, K=100.0):
    """evaluate() con simulazione e finestre sostituite da numeri scritti a mano."""
    sim = bt.SimResult(months, values, final_net)
    monkeypatch.setattr(bt, "simulate", lambda *a, **k: sim)
    monkeypatch.setattr(bt, "window_finals",
                        lambda *a, **k: [{"start": "-", "end": "-", "final_net": v} for v in window_nets])
    return bt.evaluate(None, {}, months[0], months[-1], liq_growth, K)


def test_criteria_thresholds_are_inclusive(monkeypatch):
    # 61 mesi (2001-01..2006-01), K = 100. V: 100, poi 90, 75 a dicembre 2001, 90..., 100 al mese 60.
    # caduta = 1 - 75/100 = 0,25 esatto (soglia inclusa: passa)
    # 2001: 75/100 - 1 = -0,25 esatto. -0,20 non si può ottenere esatto in virgola mobile,
    #       quindi la regola "soglia inclusa" si prova con la soglia spostata a -0,25.
    # sotto il massimo dal mese 0 al mese 60: 60 mesi (60 passa)
    # guadagno: (161,051/100)^(12/60) - 1 = 1,1 - 1 = 10%; LIQ uguale: "più alto" è stretto, non passa
    # finestre: 9 sopra K e 1 sotto: quota 9/10 = 0,9 esatta (soglia inclusa: passa)
    months = bt.months_between("2001-01", "2006-01")
    values = [100.0] + [90.0] * 10 + [75.0] + [90.0] * 48 + [100.0]
    monkeypatch.setattr(bt, "WORST_YEAR_LIMIT", -0.25)
    growth = bt.annual_growth(161.051, 100.0, 60)
    ev = _evaluate_with(monkeypatch, months, values, 161.051, [101.0] * 9 + [99.0], growth)
    assert ev["max_drawdown"] == 0.25
    assert ev["calendar_years"][2001] == -0.25
    assert ev["longest_underwater_months"] == 60
    assert ev["annual_growth"] == pytest.approx(0.10)
    assert ev["windows_share"] == 0.9
    assert ev["criteria"] == {"1_max_drawdown": True, "2_calendar_years": True, "3_underwater": True,
                              "4_beats_liq": False, "5_windows": True}
    # una finestra che finisce esattamente a K non è "sopra K": 8 su 10 = 0,8, non passa
    ev = _evaluate_with(monkeypatch, months, values, 161.051, [101.0] * 8 + [100.0, 99.0], growth)
    assert ev["windows_above_K"] == 8
    assert ev["windows_share"] == 0.8
    assert ev["criteria"]["5_windows"] is False


def test_last_december_and_unrecovered_drawdowns(monkeypatch):
    # anno 2001 che finisce a dicembre: V_dicembre = 110, valore finale netto 105:
    # l'anno usa V_m (110/100 - 1 = +10%), non il netto (sarebbe +5%)
    months = bt.months_between("2001-01", "2001-12")
    ev = _evaluate_with(monkeypatch, months, [100.0] * 11 + [110.0], 105.0, [101.0], 0.0)
    assert ev["calendar_years"] == {2001: pytest.approx(0.10)}
    # discesa mai recuperata di 61 mesi: conta e fa fallire il criterio 3
    months = bt.months_between("2001-01", "2006-02")
    ev = _evaluate_with(monkeypatch, months, [100.0] + [90.0] * 61, 90.0, [101.0], 0.0)
    assert ev["underwater"] == [{"peak": 0, "end": 61, "months": 61, "recovered": False}]
    assert ev["criteria"]["3_underwater"] is False
    assert ev["not_yet_recovered"] == []
    # discesa non recuperata di 59 mesi: non fa fallire, si scrive "non ancora recuperata"
    months = bt.months_between("2001-01", "2005-12")
    ev = _evaluate_with(monkeypatch, months, [100.0] + [90.0] * 59, 90.0, [101.0], 0.0)
    assert ev["criteria"]["3_underwater"] is True
    assert ev["not_yet_recovered"] == [{"peak_month": "2001-01", "months": 59}]


def test_pick_winner_exact_gap_and_equal_drawdown():
    # distanza esattamente 0,005 (0,005 - 0,0 è esatto): non è "sotto" 0,005 -> vince il guadagno
    assert bt.pick_winner({"A": _ev(0.005, 0.30), "B": _ev(0.0, 0.10)}) == "A"
    # distanza 0,002 e stessa caduta: vince il primo per guadagno (A), anche se B è prima nel dizionario
    assert bt.pick_winner({"B": _ev(0.050, 0.20), "A": _ev(0.052, 0.20)}) == "A"


def test_compare_two_uses_same_rule_without_pass_filter():
    assert bt.compare_two("A", _ev(0.060, 0.30), "D", _ev(0.050, 0.10)) == "A"    # 1 punto: guadagno
    assert bt.compare_two("A", _ev(0.060, 0.30), "D", _ev(0.0559, 0.10)) == "D"   # 0,41 punti: caduta
    assert bt.compare_two("A", _ev(0.060, 0.30, False), "D", _ev(0.050, 0.10)) == "A"  # niente filtro


def test_info_measures_are_wired_correctly():
    t = _fake_table("2000-12", "2006-12")
    p = ("2001-01", "2006-12")
    m = bt.all_measures(t, period_long=p, period_short=p)
    r, rd = bt.monthly_returns(t), bt.monthly_returns(t, dividends=True)
    a = m["periods"]["long"]["portfolios"]["A"]
    assert a["no_rebalance"] == bt.info_measures(r, bt.PORTFOLIOS["A"], *p, rebalance=False)
    assert a["with_estimated_dividends"] == bt.info_measures(rd, bt.PORTFOLIOS["A"], *p)
    assert a["no_rebalance"]["final_net"] != a["evaluation"]["final_net"]
    assert a["with_estimated_dividends"]["final_net"] > a["evaluation"]["final_net"]
