"""Prova 4b - controllo descrittivo della candela a martello "solo forma": stesse regole di uscita (stop al minimo
del giorno meno lo 0,1% come stop_reference della skill, uscita alla chiusura del 5o giorno) ma entrate in giorni
presi a caso, 20 ripetizioni con lo stesso numero di operazioni. Serve a capire se il risultato viene dalla
candela o solo dalla salita del mercato (solo acquisti). Costi doppi del mercato.
Uso: python3 t4b_martello_controllo.py <EURUSD|BTC>
"""
import sys
import numpy as np
import pandas as pd
from mercati import load, swap_cost

MKT = sys.argv[1]
base, cfg = load(MKT)
d1 = base.resample('1D').agg(dict(open='first', high='max', low='min', close='last', sp='median')).dropna(subset=['open'])
if MKT == 'EURUSD':
    d1 = d1[d1.index.dayofweek < 5]
d1 = d1.reset_index()
real = pd.read_csv(f'../{MKT}/t4_martello_geometria.csv', parse_dates=['time'])


def trade(i):
    entry, stop = d1.close[i], d1.low[i] * (1 - 0.001)
    dist = entry - stop
    if dist <= 0:
        return None
    for k in range(i + 1, min(i + 6, len(d1))):
        if d1.open[k] <= stop:
            r, kk = (d1.open[k] - entry) / dist, k; break
        if d1.low[k] <= stop:
            r, kk = -1.0, k; break
    else:
        kk = min(i + 5, len(d1) - 1)
        r = (d1.close[kk] - entry) / dist
    nights = (d1.time[kk] - d1.time[i]).days
    cost = (d1.sp[i] + swap_cost(cfg, 1, entry, nights)) / dist
    return kk, r - 2 * cost


rng = np.random.default_rng(11)
sums = []
for rep in range(20):
    days = np.sort(rng.choice(np.arange(130, len(d1) - 1), size=3 * len(real), replace=False))
    tot, n, free = 0.0, 0, 0
    for i in days:
        if i < free:
            continue
        r = trade(i)
        if r is None:
            continue
        free = r[0] + 1
        tot += r[1]; n += 1
        if n == len(real):
            break
    sums.append(tot)
print(f"{cfg['nome']} martello solo forma: reale {real.R.sum():+.1f}R su {len(real)} operazioni (costi doppi)")
print(f"entrate a caso (20 ripetizioni, stesso numero di operazioni): mediana {np.median(sums):+.1f}R, "
      f"min {min(sums):+.1f}R, max {max(sums):+.1f}R, prove casuali sotto il reale: {sum(s < real.R.sum() for s in sums)}/20")
