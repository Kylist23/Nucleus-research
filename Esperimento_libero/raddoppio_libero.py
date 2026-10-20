"""Esperimento libero (14/10/2026): si puo' raddoppiare 10.000 euro sull'oro 2016-2022?
Metodo scelto PRIMA di eseguire: le regole e la leva si scelgono SOLO sul 2016-2019;
poi si provano senza ritocchi sul 2020-2022, dati mai usati per scegliere.
Candidati (solo acquisti: l'oro ha una deriva al rialzo di lungo periodo e vendere allo scoperto la combatte):
  BH        compra e tieni
  TR50/100/200  comprati se la chiusura e' sopra la media a N giorni, altrimenti fuori
  RSI2      comprati se sopra la media a 200 giorni e RSI(2) < 10; esci quando chiude sopra la media a 5 giorni
Leva costante 1, 1.5, 2, 2.5, 3 (ribilanciata a ogni entrata e il primo giorno di ogni mese).
Scelta: il candidato con il rendimento piu' alto nel 2016-2019 con perdita massima dal picco non oltre il 30%.
Costi realistici (una volta): spread reale (minimo 0,20 $) per ogni oncia comprata o venduta / 2 per lato,
swap degli acquisti 3% l'anno del valore (stima: da verificare nel tester), cambio EUR/USD della BCE.
Uso: python3 -I raddoppio_libero.py <M5 csv> <stooq xauusd_d.csv> <BCE csv> [swap_annuo]
"""
import sys, itertools
import numpy as np, pandas as pd

M5, STOOQ, ECB = sys.argv[1:4]
ARG = sys.argv[4] if len(sys.argv) > 4 else '0.03'
# '12.6pt' = swap del broker in punti per lotto a notte (1 punto = 0,01 $ x 100 once = 1 $ per lotto)
SWAP_PT = float(ARG[:-2]) if ARG.endswith('pt') else None
SWAP = 0.0 if SWAP_PT is not None else float(ARG)
CAP0, MIN_SP, MAX_DD = 10_000.0, 0.20, 0.30

m5 = pd.read_csv(M5); m5['time'] = pd.to_datetime(m5.time, format='%Y.%m.%d %H:%M')
m5 = m5[m5.time >= '2016-01-01']; m5['day'] = m5.time.dt.normalize(); m5['sp'] = m5.spread_points * 0.01
d = m5[m5.time.dt.hour >= 1].groupby('day').agg(open=('open', 'first'), sp=('sp', 'first')).join(
    m5[m5.time.dt.hour <= 22].groupby('day').agg(close=('close', 'last')), how='inner')
st = pd.read_csv(STOOQ, parse_dates=['Date']).set_index('Date').loc['2014-06-01':'2015-12-31', 'Close']
c = pd.concat([st, d.close])
for n in (5, 50, 100, 200):
    d[f'sma{n}'] = c.rolling(n).mean().reindex(d.index)
delta = c.diff(); up = delta.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-delta.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
d['rsi2'] = (100 - 100 / (1 + up / dn)).reindex(d.index)
fx = pd.read_csv(ECB, usecols=['TIME_PERIOD', 'OBS_VALUE'], parse_dates=['TIME_PERIOD']).set_index('TIME_PERIOD').OBS_VALUE.astype(float)
d['fx'] = fx.reindex(d.index, method='ffill')

def signals(name):
    if name == 'BH': return pd.Series(1, index=d.index)
    if name.startswith('TR'): return (d.close > d[f'sma{name[2:]}']).astype(int)
    s, pos = [], 0
    for cl, s200, s5, r in zip(d.close, d.sma200, d.sma5, d.rsi2):
        if pos == 0 and cl > s200 and r < 10: pos = 1
        elif pos == 1 and cl > s5: pos = 0
        s.append(pos)
    return pd.Series(s, index=d.index)

def run(sig, lev, start, end):
    idx = d.loc[start:end].index
    eq, q, curve, n_tr = CAP0, 0.0, [], 0
    for i, t in enumerate(idx):
        o, rate = d.open[t], d.fx[t]
        if i:
            p = idx[i - 1]
            nights = (t - p).days
            sw = q * SWAP_PT / 100 * nights if SWAP_PT is not None else SWAP * q * d.open[p] * nights / 365
            eq += q * (o - d.open[p]) / rate - sw / rate
        want = sig.shift(1).get(t, 0) if i else 0
        new_month = i and t.month != idx[i - 1].month
        target = lev * eq * rate / o if want == 1 and eq > 0 else 0.0
        if (want == 1) != (q > 0) or (q > 0 and new_month):
            if q == 0 and target > 0: n_tr += 1
            eq -= abs(target - q) * max(d.sp[t], MIN_SP) / 2 / rate
            q = target
        curve.append(eq)
        if eq <= 0: break
    cur = pd.Series(curve, index=idx[:len(curve)])
    return cur, n_tr

def stats(cur):
    return cur.iloc[-1] / CAP0, (cur / cur.cummax() - 1).min()

names = ['BH', 'TR50', 'TR100', 'TR200', 'RSI2']
levs = [1, 1.5, 2, 2.5, 3]
rows = []
for nm, L in itertools.product(names, levs):
    cur, n = run(signals(nm), L, '2016-01-01', '2019-12-31')
    m, dd = stats(cur); rows.append((nm, L, m, dd, n))
ins = pd.DataFrame(rows, columns=['regola', 'leva', 'multiplo', 'perdita_max', 'entrate'])
print((f"Swap acquisti {SWAP_PT} $ per lotto a notte" if SWAP_PT is not None else f"Swap acquisti {SWAP:.1%} l'anno") + ". SCELTA SUL 2016-2019 (in campione):")
print(ins.round(3).to_string(index=False))
ok = ins[ins.perdita_max >= -MAX_DD]
best = ok.sort_values('multiplo').iloc[-1]
print(f"\nScelto: {best.regola} con leva {best.leva} (2016-2019: x{best.multiplo:.2f}, perdita max {best.perdita_max:.1%})")
sig = signals(best.regola)
oos, n2 = run(sig, best.leva, '2020-01-01', '2022-12-31')
full, n3 = run(sig, best.leva, '2016-01-01', '2022-12-31')
m, dd = stats(oos); print(f"FUORI CAMPIONE 2020-2022: x{m:.2f}, perdita max {dd:.1%}, entrate {n2}")
m, dd = stats(full); print(f"PERIODO INTERO 2016-2022: 10.000 -> {full.iloc[-1]:,.0f} euro (x{m:.2f}), perdita max {dd:.1%}, entrate {n3}")
yr = full.groupby(full.index.year).last(); prev = pd.concat([pd.Series({2015: CAP0}), yr]).shift(1).dropna()
print('   per anno:', {int(k): f"{yr[k] / prev[k] - 1:+.0%}" for k in yr.index})
print('\nPer confronto, sul periodo intero con la stessa leva:')
for nm in names:
    cur, n = run(signals(nm), best.leva, '2016-01-01', '2022-12-31'); m, dd = stats(cur)
    print(f"   {nm:6s} x{m:.2f} perdita max {dd:.1%} entrate {n}")
