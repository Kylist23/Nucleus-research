"""Serie CR, tentativo 1: Bitcoin sopra/sotto la media a N giorni, decisione a fine settimana.
Criteri registrati nel Manuale (cap. 10) il 17/10/2026 18:45 UTC, prima di questo calcolo.
Uso: python3 -I cr1_media200.py <percorso btcusd_d.csv>
"""
import sys
import pandas as pd

INIZIO, FINE_ESCLUSA = "2014-01-01", "2023-01-01"   # cassaforte: dal 2023 in poi scartata
CAPITALE, COSTO = 10_000.0, 0.01                   # 0,5% raddoppiato


def carica(path):
    d = pd.read_csv(path, parse_dates=["Date"])
    d = d[d.Date < FINE_ESCLUSA].reset_index(drop=True)   # prima di ogni calcolo
    assert d.Date.max() < pd.Timestamp(FINE_ESCLUSA)
    return d


def strategia(d, n=200, ritardo=0, prezzi=None, operazioni=None):
    """prezzi: prezzi di valutazione (per esempio in euro); i segnali usano sempre d.Close in dollari."""
    c = d.Close.to_numpy()
    p = c if prezzi is None else prezzi
    sma = d.Close.rolling(n).mean().to_numpy()            # include la chiusura del giorno: nota a fine giornata
    settimana = d.Date.dt.to_period("W-SUN")
    fine_sett = (settimana != settimana.shift(-1)).to_numpy()
    s = int(d.index[d.Date >= INIZIO][0])
    esecuzioni = {}                                       # riga di esecuzione -> posizione voluta
    for i in range(s, len(d)):
        if fine_sett[i] and sma[i] == sma[i]:
            j = i + 1 + ritardo
            if j < len(d):
                esecuzioni[j] = 1 if c[i] > sma[i] else 0
    cassa, unita, pos, cambi, valori = CAPITALE, 0.0, 0, 0, []
    for i in range(s, len(d)):
        voluta = esecuzioni.get(i, pos)
        if voluta != pos:
            if voluta == 1:
                entrata, unita, cassa = (d.Date[i], cassa), cassa * (1 - COSTO) / p[i], 0.0
            else:
                cassa, unita = unita * p[i] * (1 - COSTO), 0.0
                if operazioni is not None:
                    operazioni.append((entrata[0], d.Date[i], entrata[1], cassa))
            pos, cambi = voluta, cambi + 1
        valori.append(cassa + unita * p[i])
    if operazioni is not None and pos == 1:
        operazioni.append((entrata[0], None, entrata[1], valori[-1]))
    return pd.Series(valori, index=d.Date[s:].to_numpy()), cambi


def compra_e_tieni(d):
    x = d[d.Date >= INIZIO]
    return pd.Series(CAPITALE * (1 - COSTO) * x.Close.to_numpy() / x.Close.iloc[0], index=x.Date.to_numpy())


def pac(d):
    x = d[d.Date >= INIZIO].copy()
    mese = x.Date.dt.to_period("M")
    primi = x[mese != mese.shift(1)]
    rata = CAPITALE / len(primi)
    unita = (rata * (1 - COSTO) / primi.Close).sum()
    return len(primi), unita * x.Close.iloc[-1]


def calo_max(v):
    return float((v / v.cummax() - 1).min())


def rend(v, da, a):
    base = v[v.index < da]
    v0 = base.iloc[-1] if len(base) else CAPITALE
    return float(v[v.index <= a].iloc[-1] / v0 - 1)


def esame(v):
    return {
        "finale": float(v.iloc[-1]),
        "r_14_18": rend(v, "2014-01-01", "2018-12-31"),
        "r_19_22": rend(v, "2019-01-01", "2022-12-31"),
        "r_20_22": rend(v, "2020-01-01", "2022-12-31"),
        "calo_max": calo_max(v),
    }


def main(path):
    d = carica(path)
    v, cambi = strategia(d)
    bh = compra_e_tieni(d)
    e, eb = esame(v), esame(bh)
    print(f"Dati: {d.Date.min().date()} .. {d.Date.max().date()}, righe {len(d)}")
    print(f"CR1 (media 200): finale {e['finale']:,.0f} $, cambi {cambi}, calo max {e['calo_max']:.1%}")
    print(f"  2014-2018 {e['r_14_18']:+.1%}  2019-2022 {e['r_19_22']:+.1%}  2020-2022 {e['r_20_22']:+.1%}")
    print(f"Compra e tieni: finale {eb['finale']:,.0f} $, calo max {eb['calo_max']:.1%}")
    print(f"  2014-2018 {eb['r_14_18']:+.1%}  2019-2022 {eb['r_19_22']:+.1%}")
    mesi, fin_pac = pac(d)
    print(f"PAC: {mesi} rate, investiti {CAPITALE:,.0f} $, finale {fin_pac:,.0f} $")
    k = [e["finale"] > CAPITALE, e["r_14_18"] > 0 and e["r_19_22"] > 0,
         e["calo_max"] >= -0.50, e["calo_max"] - eb["calo_max"] >= 0.20]
    for n_, ok in zip(["(1) finale > 10.000", "(2) due periodi positivi", "(3) calo max <= 50%",
                       "(4) calo max 20 punti meglio di compra e tieni"], k):
        print(f"  {n_}: {'SUPERATO' if ok else 'NON superato'}")
    print("Anno per anno (CR1 / compra e tieni):")
    for a in range(2014, 2023):
        print(f"  {a}: {rend(v, f'{a}-01-01', f'{a}-12-31'):+.1%} / {rend(bh, f'{a}-01-01', f'{a}-12-31'):+.1%}")
    print("Robustezza:")
    passa = 0
    for n in (100, 150, 250, 300):
        vn, cn = strategia(d, n)
        en = esame(vn)
        ok = en["finale"] > CAPITALE and en["calo_max"] >= -0.50
        passa += ok
        print(f"  media {n}: finale {en['finale']:,.0f} $, calo max {en['calo_max']:.1%}, cambi {cn} -> {'ok' if ok else 'no'}")
    print(f"  varianti che superano (1) e (3): {passa}/4 (soglia 3)")
    print(f"  ultimo terzo 2020-2022: {e['r_20_22']:+.1%} (soglia > 0)")
    vr, _ = strategia(d, 200, ritardo=1)
    print(f"  un giorno di ritardo: finale {vr.iloc[-1]:,.0f} $ (soglia > 10.000)")
    v.rename("CR1").to_frame().assign(compra_e_tieni=bh).to_csv("cr1_curva.csv", index_label="Date")


if __name__ == "__main__":
    main(sys.argv[1])
