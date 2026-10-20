"""CR1 in euro: stessa regola registrata (segnali sul Bitcoin in dollari), valori convertiti in euro
con il cambio di riferimento BCE (USD per 1 EUR) dell'ultimo giorno pubblicato fino a quella data.
Non e' un nuovo tentativo: cambia solo la valuta in cui si contano guadagni e perdite.
Uso: python3 -I cr1_euro.py <btcusd_d.csv> <eur_usd_ecb_raw.csv>
"""
import os
import sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cr1_media200 import CAPITALE, COSTO, INIZIO, carica, strategia


def cambio(path):
    e = pd.read_csv(path, usecols=["TIME_PERIOD", "OBS_VALUE"], parse_dates=["TIME_PERIOD"])
    e = e.dropna().rename(columns={"TIME_PERIOD": "Date", "OBS_VALUE": "usd_per_eur"})
    return e.sort_values("Date")


def calo_euro(v):
    picco = v.cummax()
    i = (v - picco).idxmin()
    p = v[:i].idxmax()
    return v[p], v[i], p, i


def main(btc_path, ecb_path):
    d = carica(btc_path)
    d = pd.merge_asof(d.sort_values("Date"), cambio(ecb_path), on="Date", direction="backward")
    assert d.usd_per_eur.notna().all()
    eur = (d.Close / d.usd_per_eur).to_numpy()
    ops = []
    v, cambi = strategia(d, prezzi=eur, operazioni=ops)
    x = d[d.Date >= INIZIO]
    bh = pd.Series(CAPITALE * (1 - COSTO) * (x.Close / x.usd_per_eur).to_numpy() / (x.Close.iloc[0] / x.usd_per_eur.iloc[0]),
                   index=x.Date.to_numpy())
    print(f"Cambio BCE usato: da {x.usd_per_eur.iloc[0]:.4f} ({x.Date.iloc[0].date()}) a {x.usd_per_eur.iloc[-1]:.4f} ({x.Date.iloc[-1].date()}) dollari per 1 euro")
    print(f"\nCR1 in euro, capitale iniziale {CAPITALE:,.0f} euro, {cambi} cambi")
    print(f"  Capitale finale: {v.iloc[-1]:,.0f} euro  (guadagno netto {v.iloc[-1]-CAPITALE:+,.0f} euro)")
    chiuse = [o for o in ops if o[1] is not None]
    utile = [(o[3] - o[2]) for o in chiuse]
    vinc = [u for u in utile if u > 0]
    perd = [u for u in utile if u <= 0]
    costi = sum(o[2] * COSTO + o[3] * COSTO / (1 - COSTO) for o in chiuse)
    aperta = [o for o in ops if o[1] is None]
    print(f"  Operazioni chiuse: {len(chiuse)}; vincenti {len(vinc)} per {sum(vinc):+,.0f} euro; perdenti {len(perd)} per {sum(perd):+,.0f} euro")
    if aperta:
        o = aperta[0]
        print(f"  Operazione aperta al 30/12/2022 (entrata {o[0].date()}): {o[3]-o[2]:+,.0f} euro, valutata senza costo di uscita")
    print(f"  Costi pagati (1% per lato, gia' raddoppiati): {costi:,.0f} euro sulle operazioni chiuse + {aperta[0][2]*COSTO if aperta else 0:,.0f} euro di entrata dell'ultima")
    peggiore = sorted(chiuse, key=lambda o: o[3] - o[2])[:3]
    for o in peggiore:
        print(f"    perdita peggiore: {o[0].date()} -> {o[1].date()}: {o[3]-o[2]:+,.0f} euro ({o[3]/o[2]-1:+.1%})")
    a, b, pa, pb = calo_euro(v)
    print(f"  Calo massimo in euro: da {a:,.0f} ({pd.Timestamp(pa).date()}) a {b:,.0f} ({pd.Timestamp(pb).date()}): {b-a:+,.0f} euro ({b/a-1:.1%})")
    a2, b2, pa2, pb2 = calo_euro(bh)
    print(f"\nCompra e tieni in euro: finale {bh.iloc[-1]:,.0f} euro ({bh.iloc[-1]-CAPITALE:+,.0f}); calo massimo {b2-a2:+,.0f} euro ({b2/a2-1:.1%}), da {pd.Timestamp(pa2).date()} a {pd.Timestamp(pb2).date()}")
    mese = x.Date.dt.to_period("M")
    primi = x[mese != mese.shift(1)]
    rata = CAPITALE / len(primi)
    unita = (rata * (1 - COSTO) / (primi.Close / primi.usd_per_eur)).sum()
    fin = unita * x.Close.iloc[-1] / x.usd_per_eur.iloc[-1]
    print(f"PAC in euro: {len(primi)} rate da {rata:,.2f} euro, investiti {CAPITALE:,.0f}, finale {fin:,.0f} euro ({fin-CAPITALE:+,.0f})")
    print("\nAnno per anno in euro (variazione del capitale) CR1 / compra e tieni:")
    for anno in range(2014, 2023):
        def delta(s):
            prima = s[s.index < pd.Timestamp(f"{anno}-01-01")]
            v0 = prima.iloc[-1] if len(prima) else CAPITALE
            v1 = s[s.index <= pd.Timestamp(f"{anno}-12-31")].iloc[-1]
            return v1 - v0, v1 / v0 - 1
        (dc, pc), (db, pb_) = delta(v), delta(bh)
        print(f"  {anno}: {dc:+12,.0f} euro ({pc:+.1%})   /  {db:+12,.0f} euro ({pb_:+.1%})")
    pd.DataFrame(ops, columns=["entrata", "uscita", "euro_entrata", "euro_uscita"]).to_csv("cr1_operazioni_euro.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
