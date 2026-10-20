"""Simulatore dei portafogli della strada 1 (docs/STRADA1_SPEC_TEST.md, §3-§9).

Ogni formula segue la spec riga per riga; il numero del paragrafo è nei commenti.
In questa fase il simulatore si usa SOLO su prezzi inventati (test e confronto
con una seconda implementazione indipendente): niente esecuzione sui dati veri.
"""

from dataclasses import dataclass, field
from pathlib import Path
import math

import numpy as np
import pandas as pd

from src.hashing import sha256_file


ASSETS = ["spx", "sx5e", "bond", "gold", "cash", "btc"]

# §6: costo annuo del fondo (TER)
TER = {"spx": 0.0020, "sx5e": 0.0020, "bond": 0.0015, "gold": 0.0025, "btc": 0.0100, "cash": 0.0}
# §6: aliquote sui guadagni
TAX = {"spx": 0.26, "sx5e": 0.26, "bond": 0.125, "gold": 0.26, "btc": 0.26, "cash": 0.26}
TRADE_COST = 0.001      # §6: 0,10% su ogni acquisto e vendita
STAMP_DUTY = 0.002      # §6: bollo annuo 0,20%
BOND_YEARS_LEFT = 10 - 1 / 12  # §3: durata residua dopo un mese
DIVIDENDS = {"spx": 0.016, "sx5e": 0.028}  # §9: stima fissa, solo informazione

# §4: pesi obiettivo
PORTFOLIOS = {
    "A": {"spx": 0.70, "sx5e": 0.30},
    "B": {"spx": 0.42, "sx5e": 0.18, "bond": 0.40},
    "C": {"spx": 0.175, "sx5e": 0.075, "bond": 0.25, "gold": 0.25, "cash": 0.25},
    "D": {"spx": 0.385, "sx5e": 0.165, "bond": 0.20, "gold": 0.10, "cash": 0.10, "btc": 0.05},
    "LIQ": {"cash": 1.0},
    "D-core": {"spx": 0.385, "sx5e": 0.165, "bond": 0.20, "gold": 0.10, "cash": 0.15},
}

# §5: periodi (mese in cui si investe, ultimo mese)
PERIOD_LONG = ("2001-01", "2022-12")
PERIOD_SHORT = ("2014-01", "2022-12")
VAULT_START = "2023-01"

# §7: soglie (tutte incluse)
MAX_DRAWDOWN_LIMIT = 0.25
WORST_YEAR_LIMIT = -0.20
UNDERWATER_LIMIT_MONTHS = 60
WINDOW_MONTHS = 60
WINDOW_SHARE = 0.90
# §8: distanza minima tra i primi due (0,50 punti l'anno)
TIE_GAP = 0.005

K_DEFAULT = 10_000.0


class VaultError(Exception):
    """Si è chiesto un mese dal 2023-01 in poi senza allow_vault=True (§5)."""


def months_between(first: str, last: str) -> list[str]:
    return [p.strftime("%Y-%m") for p in pd.period_range(first, last, freq="M")]


def check_vault(months, allow_vault: bool = False) -> None:
    """§5: rifiuta qualsiasi mese dal 2023-01 in poi, salvo allow_vault=True."""
    if allow_vault:
        return
    bad = [m for m in months if m >= VAULT_START]
    if bad:
        raise VaultError(f"Mesi della cassaforte richiesti: {bad[0]}..{bad[-1]}")


# ---------------------------------------------------------------- §3 rendimenti

def bond_price(c: float, y: float, n: float = BOND_YEARS_LEFT) -> float:
    """Prezzo (per 1 di nominale) di un titolo con cedola annua c, al tasso y, durata n anni."""
    if abs(y) < 1e-9:
        return c * n + 1
    return c / y * (1 - (1 + y) ** (-n)) + (1 + y) ** (-n)


def bond_return(y_prev_pct: float, y_pct: float) -> float:
    """Rendimento del mese: titolo comprato alla pari al tasso del mese prima,
    rivalutato al tasso di questo mese, più un dodicesimo di cedola."""
    c = y_prev_pct / 100
    y = y_pct / 100
    return bond_price(c, y) - 1 + c / 12


def monthly_returns(table: pd.DataFrame, dividends: bool = False,
                    allow_vault: bool = False) -> pd.DataFrame:
    """Rendimenti del mese m (dal mese m-1 al mese m), in euro, per ogni attività.
    Il primo mese della tabella non ha rendimento (NaN). Usa solo i mesi m-1 e m."""
    months = list(table["month"])
    check_vault(months, allow_vault)
    if not months or months != months_between(months[0], months[-1]):
        raise ValueError("I mesi della tabella devono essere unici, in ordine e consecutivi")
    t = table.set_index("month")
    rows = {a: [math.nan] for a in ASSETS}
    for prev, cur in zip(months[:-1], months[1:]):
        rows["spx"].append(t.at[cur, "spx_eur"] / t.at[prev, "spx_eur"] - 1)
        rows["sx5e"].append(t.at[cur, "sx5e_eur"] / t.at[prev, "sx5e_eur"] - 1)
        rows["gold"].append(t.at[cur, "gold_eur"] / t.at[prev, "gold_eur"] - 1)
        rows["btc"].append(t.at[cur, "btc_eur"] / t.at[prev, "btc_eur"] - 1)
        y_prev, y_cur = t.at[prev, "y10_pct"], t.at[cur, "y10_pct"]
        rows["bond"].append(
            math.nan if pd.isna(y_prev) or pd.isna(y_cur) else bond_return(y_prev, y_cur)
        )
        rows["cash"].append(t.at[prev, "euribor3m_pct"] / 100 / 12)
    r = pd.DataFrame(rows, index=months)
    if dividends:
        for a, d in DIVIDENDS.items():
            r[a] = r[a] + d / 12
    return r


# ---------------------------------------------------------------- §6 simulazione

@dataclass
class SimResult:
    months: list            # months[0] = mese d'acquisto
    values: list            # values[0] = V_0 = K; values[i] = V del mese months[i]
    final_net: float        # dopo la vendita finale (tasse e costo)
    contributed: list = field(default_factory=list)  # totale versato fino al mese i
    holdings: list = field(default_factory=list)     # valore di ogni posizione al mese i

    @property
    def steps(self) -> int:
        return len(self.months) - 1


def _rebalance(h: dict, B: dict, weights: dict) -> None:
    """§6 passo 4: vende sopra obiettivo (con tasse e costo), compra sotto obiettivo."""
    V = sum(h.values())
    target = {a: weights[a] * V for a in h}
    proceeds = 0.0
    for a in h:
        if h[a] > target[a]:
            s = h[a] - target[a]
            gain = s * (1 - B[a] / h[a])
            tax = TAX[a] * max(gain, 0.0)
            B[a] = B[a] * (1 - s / h[a])
            h[a] = h[a] - s
            proceeds += s - tax - TRADE_COST * s
    gaps = {a: target[a] - h[a] for a in h if h[a] < target[a]}
    total_gap = sum(gaps.values())
    if total_gap <= 0:
        return
    to_buy = proceeds / (1 + TRADE_COST)
    for a, gap in gaps.items():
        amount = to_buy * gap / total_gap
        h[a] += amount
        B[a] += amount


def liquidation_value(h: dict, B: dict) -> float:
    """§6 fine: si vende tutto, tasse sui guadagni (mai sulle perdite) e costo 0,10%."""
    total = 0.0
    for a in h:
        tax = TAX[a] * max(h[a] - B[a], 0.0)
        total += h[a] - tax - TRADE_COST * h[a]
    return total


def simulate(returns: pd.DataFrame, weights: dict, start: str, end: str,
             K: float = K_DEFAULT, rebalance: bool = True,
             monthly_contribution: float = 0.0, allow_vault: bool = False) -> SimResult:
    """Simula un portafoglio dal mese `start` (acquisto) al mese `end` (vendita finale)."""
    if start >= end:
        raise ValueError(f"Il mese iniziale {start} deve venire prima di quello finale {end}")
    if start not in returns.index:
        raise ValueError(f"Il mese iniziale {start} non è nella tabella dei rendimenti")
    months = months_between(start, end)
    check_vault(months, allow_vault)
    if abs(sum(weights.values()) - 1) > 1e-9:
        raise ValueError(f"I pesi non sommano a 1: {weights}")
    assets = [a for a, w in weights.items() if w > 0]
    last = months[-1]

    # mese iniziale: si investe K / 1,001; B = importo investito
    h = {a: weights[a] * K / (1 + TRADE_COST) for a in assets}
    B = dict(h)
    total_in = K
    values = [K]
    contributed = [K]
    holdings = [dict(h)]

    for m in months[1:]:
        for a in assets:
            if m not in returns.index:
                raise ValueError(f"Rendimento mancante per {a} nel mese {m}")
            r = float(returns.at[m, a])
            if pd.isna(r):
                raise ValueError(f"Rendimento mancante per {a} nel mese {m}")
            if not math.isfinite(r) or r <= -1:
                raise ValueError(f"Rendimento non valido per {a} nel mese {m}: {r}")
            h[a] = h[a] * (1 + r)                              # 1. rendimento
            h[a] = h[a] * (1 - TER[a]) ** (1 / 12)             # 2. costo del fondo
            h[a] = h[a] * (1 - STAMP_DUTY / 12)                # 3. bollo
            B[a] = B[a] * (1 - STAMP_DUTY / 12)
        if rebalance and m.endswith("-12") and m != last:      # 4. ribilanciamento
            _rebalance(h, B, weights)
        if monthly_contribution:                                # §9 versamenti, a fine mese
            invested = monthly_contribution / (1 + TRADE_COST)
            for a in assets:
                h[a] += weights[a] * invested
                B[a] += weights[a] * invested
            total_in += monthly_contribution
        values.append(sum(h.values()))                          # 5. V_m
        contributed.append(total_in)
        holdings.append(dict(h))

    return SimResult(months, values, liquidation_value(h, B), contributed, holdings)


# ---------------------------------------------------------------- §7 misure

def max_drawdown(values: list) -> float:
    """Massimo di 1 - V_m / max(V_0..V_m)."""
    peak = values[0]
    worst = 0.0
    for v in values:
        peak = max(peak, v)
        worst = max(worst, 1 - v / peak)
    return worst


def calendar_year_returns(months: list, values: list) -> dict:
    """V_dicembre / V_dicembre dell'anno prima - 1; il primo anno parte da V_0.
    Solo gli anni il cui dicembre cade dentro la simulazione."""
    out = {}
    base = values[0]
    for m, v in zip(months[1:], values[1:]):
        if m.endswith("-12"):
            out[int(m[:4])] = v / base - 1
            base = v
    return out


def underwater_periods(values: list) -> list:
    """Ogni discesa: mesi dal mese del massimo al primo mese in cui V torna almeno a quel
    massimo. Una discesa non recuperata alla fine ha recovered=False e i mesi fino alla fine."""
    out = []
    peak_i = 0
    in_drawdown = False
    for i in range(1, len(values)):
        if values[i] >= values[peak_i]:
            if in_drawdown:
                out.append({"peak": peak_i, "end": i, "months": i - peak_i, "recovered": True})
                in_drawdown = False
            peak_i = i
        else:
            in_drawdown = True
    if in_drawdown:
        last = len(values) - 1
        out.append({"peak": peak_i, "end": last, "months": last - peak_i, "recovered": False})
    return out


def annual_growth(final_net: float, K: float, steps: int) -> float:
    """(valore finale netto / K)^(12/passi) - 1."""
    return (final_net / K) ** (12 / steps) - 1


def window_finals(returns: pd.DataFrame, weights: dict, start: str, end: str,
                  K: float = K_DEFAULT, allow_vault: bool = False) -> list:
    """§7.5: una simulazione nuova per ogni mese di partenza s con s + 60 entro la fine."""
    months = months_between(start, end)
    finals = []
    for i in range(len(months) - WINDOW_MONTHS):
        r = simulate(returns, weights, months[i], months[i + WINDOW_MONTHS], K,
                     allow_vault=allow_vault)
        finals.append({"start": months[i], "end": months[i + WINDOW_MONTHS],
                       "final_net": r.final_net})
    return finals


def check_criteria(dd: float, years: dict, underwater: list, growth: float,
                   liq_growth: float, window_finals_net: list, K: float) -> dict:
    """I 5 criteri del §7. Tutte le soglie incluse, numeri senza arrotondare."""
    share = (sum(f > K for f in window_finals_net) / len(window_finals_net)
             if window_finals_net else None)
    return {
        "1_max_drawdown": dd <= MAX_DRAWDOWN_LIMIT,
        "2_calendar_years": all(r >= WORST_YEAR_LIMIT for r in years.values()),
        "3_underwater": all(u["months"] <= UNDERWATER_LIMIT_MONTHS for u in underwater),
        "4_beats_liq": growth > liq_growth,
        "5_windows": share is not None and share >= WINDOW_SHARE,
    }


def evaluate(returns: pd.DataFrame, weights: dict, start: str, end: str,
             liq_growth: float, K: float = K_DEFAULT, allow_vault: bool = False) -> dict:
    """Le 5 misure del §7 e i criteri (tutte le soglie incluse)."""
    sim = simulate(returns, weights, start, end, K, allow_vault=allow_vault)
    dd = max_drawdown(sim.values)
    years = calendar_year_returns(sim.months, sim.values)
    under = underwater_periods(sim.values)
    growth = annual_growth(sim.final_net, K, sim.steps)
    windows = window_finals(returns, weights, start, end, K, allow_vault)
    share = sum(w["final_net"] > K for w in windows) / len(windows) if windows else math.nan

    longest = max((u["months"] for u in under), default=0)
    still_down = [u for u in under if not u["recovered"]]
    criteria = check_criteria(dd, years, under, growth, liq_growth,
                              [w["final_net"] for w in windows], K)
    return {
        "start": start, "end": end, "steps": sim.steps,
        "final_net": sim.final_net,
        "annual_growth": growth,
        "liq_annual_growth": liq_growth,
        "max_drawdown": dd,
        "calendar_years": years,
        "worst_year": min(years.values()) if years else None,
        "underwater": under,
        "longest_underwater_months": longest,
        "not_yet_recovered": [
            {"peak_month": sim.months[u["peak"]], "months": u["months"]}
            for u in still_down if u["months"] <= UNDERWATER_LIMIT_MONTHS
        ],
        "windows": len(windows),
        "windows_above_K": sum(w["final_net"] > K for w in windows),
        "windows_share": share,
        "criteria": criteria,
        "passes_all": all(criteria.values()),
    }


# ---------------------------------------------------------------- §8 chi vince

def pick_winner(candidates: dict) -> str | None:
    """Tra quelli che passano vince il guadagno medio annuo più alto; se i primi due
    distano meno di 0,50 punti l'anno vince quello con la caduta massima più piccola."""
    passing = sorted(
        (name for name, ev in candidates.items() if ev["passes_all"]),
        key=lambda n: candidates[n]["annual_growth"], reverse=True,
    )
    if not passing:
        return None
    if len(passing) == 1:
        return passing[0]
    first, second = passing[0], passing[1]
    if candidates[first]["annual_growth"] - candidates[second]["annual_growth"] < TIE_GAP:
        return min((first, second), key=lambda n: candidates[n]["max_drawdown"])
    return first


def compare_two(a_name: str, a_eval: dict, b_name: str, b_eval: dict) -> str:
    """Stessa regola di pick_winner, tra due portafogli, senza il filtro 'passa tutto'."""
    first, second = sorted([(a_name, a_eval), (b_name, b_eval)],
                           key=lambda x: x[1]["annual_growth"], reverse=True)
    if first[1]["annual_growth"] - second[1]["annual_growth"] < TIE_GAP:
        return min((first, second), key=lambda x: x[1]["max_drawdown"])[0]
    return first[0]


# ---------------------------------------------------------------- §9 informazione

def info_measures(returns: pd.DataFrame, weights: dict, start: str, end: str,
                  K: float = K_DEFAULT, rebalance: bool = True,
                  allow_vault: bool = False) -> dict:
    sim = simulate(returns, weights, start, end, K, rebalance=rebalance, allow_vault=allow_vault)
    return {
        "final_net": sim.final_net,
        "annual_growth": annual_growth(sim.final_net, K, sim.steps),
        "max_drawdown": max_drawdown(sim.values),
    }


def contribution_measures(returns: pd.DataFrame, weights: dict, start: str, end: str,
                          K: float = K_DEFAULT, monthly: float = 200.0,
                          allow_vault: bool = False) -> dict:
    """§9: K all'inizio e `monthly` alla fine di ogni mese successivo."""
    sim = simulate(returns, weights, start, end, K, monthly_contribution=monthly,
                   allow_vault=allow_vault)
    ratios = [v / c - 1 for v, c in zip(sim.values, sim.contributed)]
    worst_i = min(range(len(ratios)), key=lambda i: ratios[i])
    return {
        "total_contributed": sim.contributed[-1],
        "final_net": sim.final_net,
        "worst_vs_contributed": ratios[worst_i],
        "worst_month": sim.months[worst_i],
    }


# ---------------------------------------------------------------- tutte le misure

def all_measures(table: pd.DataFrame, K: float = K_DEFAULT,
                 period_long: tuple = PERIOD_LONG, period_short: tuple = PERIOD_SHORT,
                 allow_vault: bool = False) -> dict:
    """Dati i prezzi mensili (stesse colonne di path1_monthly.csv), restituisce tutte le
    misure della spec per tutti i portafogli. Serve per il confronto con la seconda
    implementazione su prezzi inventati."""
    r = monthly_returns(table, allow_vault=allow_vault)
    r_div = monthly_returns(table, dividends=True, allow_vault=allow_vault)
    plan = {
        "long": (period_long, ["A", "B", "C", "LIQ", "D-core"]),
        "short": (period_short, ["A", "B", "C", "D", "LIQ"]),
    }
    out = {"K": K, "periods": {}}
    for label, ((start, end), names) in plan.items():
        liq_sim = simulate(r, PORTFOLIOS["LIQ"], start, end, K, allow_vault=allow_vault)
        liq_growth = annual_growth(liq_sim.final_net, K, liq_sim.steps)
        res = {}
        for name in names:
            w = PORTFOLIOS[name]
            res[name] = {
                "evaluation": evaluate(r, w, start, end, liq_growth, K, allow_vault),
                "no_rebalance": info_measures(r, w, start, end, K, rebalance=False,
                                              allow_vault=allow_vault),
                "with_estimated_dividends": info_measures(r_div, w, start, end, K,
                                                          allow_vault=allow_vault),
                "monthly_contributions": contribution_measures(r, w, start, end, K,
                                                               allow_vault=allow_vault),
            }
        out["periods"][label] = {"start": start, "end": end, "portfolios": res}

    out["verdict"] = verdict(
        {n: out["periods"]["long"]["portfolios"][n]["evaluation"] for n in ("A", "B", "C")},
        {n: out["periods"]["short"]["portfolios"][n]["evaluation"] for n in ("A", "B", "C", "D")},
    )

    # §13: verdetto prudente, calcolato con i soli prezzi e con i dividendi stimati
    prices_long = {n: out["periods"]["long"]["portfolios"][n]["evaluation"]
                   for n in PRUDENT_LONG}
    prices_short = {n: out["periods"]["short"]["portfolios"][n]["evaluation"]
                    for n in ("A", "B", "C", "D", "LIQ")}
    prices_short["D-core"] = _evaluate_set(r, period_short, ["D-core"], K, allow_vault)["D-core"]
    versions = {
        "prices": (prices_long, prices_short),
        "dividends": (
            _evaluate_set(r_div, period_long, PRUDENT_LONG, K, allow_vault),
            _evaluate_set(r_div, period_short, PRUDENT_SHORT, K, allow_vault),
        ),
    }
    prudence = {"versions": {}}
    for label, (long_evals, short_evals) in versions.items():
        prudence["versions"][label] = {
            "long": {"start": period_long[0], "end": period_long[1],
                     "portfolios": _with_status(long_evals)},
            "short": {"start": period_short[0], "end": period_short[1],
                      "portfolios": _with_status(short_evals)},
            "verdict": prudent_verdict(long_evals, short_evals),
        }
    prudence["final"] = combine_versions(prudence["versions"]["prices"]["verdict"],
                                         prudence["versions"]["dividends"]["verdict"])
    out["prudence"] = prudence
    return to_plain(out)


# ---------------------------------------------------------------- §13 prudenza

PRUDENT_LONG = ["A", "B", "C", "LIQ", "D-core"]
PRUDENT_SHORT = ["A", "B", "C", "D", "LIQ", "D-core"]

# §13.3: fasce "al limite", estremi compresi
BORDERLINE = {
    "1_max_drawdown": (0.22, 0.28),
    "2_calendar_years": (-0.22, -0.18),
    "3_underwater": (54, 66),
    "4_beats_liq": (-0.005, 0.005),
    "5_windows": (0.87, 0.93),
}

STATUS_CLEAR = "netto"
STATUS_BORDERLINE = "al limite"
STATUS_FAIL = "non passa"
STATUS_NONE = "nessuno"


def _evaluate_set(returns: pd.DataFrame, period: tuple, names: list, K: float,
                  allow_vault: bool) -> dict:
    """Valutazione (§7) di più portafogli sullo stesso periodo, con LIQ di quei rendimenti."""
    start, end = period
    liq_sim = simulate(returns, PORTFOLIOS["LIQ"], start, end, K, allow_vault=allow_vault)
    liq_growth = annual_growth(liq_sim.final_net, K, liq_sim.steps)
    return {n: evaluate(returns, PORTFOLIOS[n], start, end, liq_growth, K, allow_vault)
            for n in names}


def _in_band(value, band) -> bool:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return False
    low, high = band
    return low <= value <= high


def borderline_flags(ev: dict) -> dict:
    """§13.3: per ogni criterio, True se il valore cade nella fascia (estremi compresi)."""
    return {
        "1_max_drawdown": _in_band(ev["max_drawdown"], BORDERLINE["1_max_drawdown"]),
        "2_calendar_years": _in_band(ev["worst_year"], BORDERLINE["2_calendar_years"]),
        "3_underwater": _in_band(ev["longest_underwater_months"], BORDERLINE["3_underwater"]),
        "4_beats_liq": _in_band(ev["annual_growth"] - ev["liq_annual_growth"],
                                BORDERLINE["4_beats_liq"]),
        "5_windows": _in_band(ev["windows_share"], BORDERLINE["5_windows"]),
    }


def portfolio_status(ev: dict) -> str:
    """'netto' se passa e nessun criterio è al limite; 'al limite' se passa con almeno
    un criterio al limite; 'non passa' se non passa tutti e 5 i criteri."""
    if not ev["passes_all"]:
        return STATUS_FAIL
    return STATUS_BORDERLINE if any(borderline_flags(ev).values()) else STATUS_CLEAR


def _with_status(evals: dict) -> dict:
    return {n: {"evaluation": ev, "borderline": borderline_flags(ev),
                "status": portfolio_status(ev)} for n, ev in evals.items()}


def pick_winner_prudent(candidates: dict) -> tuple:
    """§13.3 + §8: un portafoglio netto batte sempre uno al limite; tra portafogli con lo
    stesso stato vale pick_winner. Restituisce (nome, stato) oppure (None, None)."""
    for status in (STATUS_CLEAR, STATUS_BORDERLINE):
        same = {n: ev for n, ev in candidates.items() if portfolio_status(ev) == status}
        winner = pick_winner(same)
        if winner is not None:
            return winner, status
    return None, None


def prudent_verdict(long_evals: dict, short_evals: dict) -> dict:
    """§8 con le regole del §13 per UNA versione (solo prezzi o con dividendi).
    `long_evals` deve contenere A, B, C, D-core; `short_evals` A, B, C, D, D-core."""
    winner_long, winner_status = pick_winner_prudent(
        {n: long_evals[n] for n in ("A", "B", "C")})
    d_eval = short_evals["D"]
    d_status = portfolio_status(d_eval)
    d_core_long_passes = bool(long_evals["D-core"]["passes_all"])
    d_eligible = bool(d_eval["passes_all"]) and d_core_long_passes   # §13.2

    if not d_eligible:
        final, final_status = winner_long, winner_status
    elif winner_long is None:
        final, final_status = "D", d_status
    elif d_status != winner_status:
        # netto batte sempre al limite; il vincitore del punto 1 porta il suo stato
        final, final_status = ((winner_long, winner_status) if winner_status == STATUS_CLEAR
                               else ("D", d_status))
    else:
        final = compare_two(winner_long, short_evals[winner_long], "D", d_eval)
        final_status = winner_status if final == winner_long else d_status

    return {
        "winner_A_B_C_long": winner_long,
        "winner_A_B_C_long_status": winner_status,
        "D_passes_short": bool(d_eval["passes_all"]),
        "D_status_short": d_status,
        "D_core_passes_long": d_core_long_passes,
        "D_eligible": d_eligible,
        "bitcoin_contribution": (short_evals["D"]["annual_growth"]
                                 - short_evals["D-core"]["annual_growth"]),
        "winner": final,
        "status": final_status,
    }


def combine_versions(prices: dict, dividends: dict) -> dict:
    """§13.1 e §13.4: accordo tra la versione con i soli prezzi e quella con i dividendi."""
    a, b = prices["winner"], dividends["winner"]
    agree = a == b
    if agree and a is None:
        winner, status = None, STATUS_NONE
    elif agree:
        both_clear = prices["status"] == STATUS_CLEAR and dividends["status"] == STATUS_CLEAR
        winner, status = a, (STATUS_CLEAR if both_clear else STATUS_BORDERLINE)
    else:
        winner, status = None, STATUS_BORDERLINE

    def name(x):
        return x if x is not None else "nessuno"

    if status == STATUS_NONE:
        sentence = "Nessun vincitore: nessun portafoglio vince in nessuna delle due versioni."
    elif winner is None:
        sentence = (f"Nessun vincitore, al limite: le due versioni non sono d'accordo "
                    f"(solo prezzi: {name(a)}; con dividendi stimati: {name(b)}).")
    elif status == STATUS_CLEAR:
        sentence = f"Vincitore: {winner}, netto in tutte e due le versioni."
    else:
        sentence = (f"Vincitore: {winner}, al limite (solo prezzi: {prices['status']}; "
                    f"con dividendi stimati: {dividends['status']}).")
    if winner == "D":
        sentence += " D non ha attraversato il 2008."
    return {
        "winner_prices": a,
        "status_prices": prices["status"],
        "winner_dividends": b,
        "status_dividends": dividends["status"],
        "versions_agree": agree,
        "final_winner": winner,
        "final_status": status,
        "sentence": sentence,
    }


def verdict(long_evals: dict, short_evals: dict) -> dict:
    """§8: A, B, C sul periodo lungo; poi D sul periodo breve contro il vincitore.
    `long_evals`: valutazioni di A, B, C sul periodo lungo.
    `short_evals`: valutazioni di D e del vincitore (o di A, B, C) sul periodo breve."""
    winner_long = pick_winner({n: long_evals[n] for n in ("A", "B", "C")})
    d_eval = short_evals["D"]
    if not d_eval["passes_all"]:
        final = winner_long
    elif winner_long is None:
        final = "D"
    else:
        final = compare_two(winner_long, short_evals[winner_long], "D", d_eval)
    return {
        "winner_A_B_C_long": winner_long,
        "D_passes_short": bool(d_eval["passes_all"]),
        "final_winner": final,
        "note": "D non ha attraversato il 2008.",
    }


def to_plain(obj):
    """Converte i risultati in soli tipi Python (niente tipi numpy), per json.dumps."""
    if isinstance(obj, dict):
        return {(to_plain(k) if not isinstance(k, str) else k): to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_plain(v) for v in obj]
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return float(obj)
    return obj


def load_monthly_table(path: Path, expected_sha256: str) -> pd.DataFrame:
    """Legge path1_monthly.csv dopo averne controllato lo SHA-256, senza perdere cifre."""
    actual = sha256_file(Path(path))
    if actual != expected_sha256:
        raise ValueError(f"SHA-256 della tabella diverso: {actual} invece di {expected_sha256}")
    return pd.read_csv(path, dtype={"month": str}, float_precision="round_trip")
