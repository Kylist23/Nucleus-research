"""Prova 6 - Serie F (apertura di New York), G (dollaro), H (rimbalzo) rifatte su EUR/USD o Bitcoin.
Stesse regole di 1_Bot/Scrematura_Python/screen_FGH.py (compresa la correzione degli orari: prima candela entro
15 minuti dopo l'orario di entrata, ultima entro 30 minuti prima dell'orario di uscita), con costi e ore del
mercato (mercati.py). Adattamento di G registrato prima del calcolo: su EUR/USD si segue per 24 ore il movimento
dell'EUR/USD BCE (almeno 0,5%: compra se sale, vende se scende); su Bitcoin come sull'oro (compra se l'euro/dollaro
sale, cioe' il dollaro si indebolisce; vende se scende).
Uso: python3 t6_FGH.py <EURUSD|BTC> <eur_usd_ecb_raw.csv> [fattore_soglia fattore_stop]
"""
import sys
import numpy as np
import pandas as pd
from mercati import load, swap_cost, summary

MKT, ECB_PATH = sys.argv[1], sys.argv[2]
KT = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
KS = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0

base, cfg = load(MKT, warmup_days=40)
NOTRADE = set(cfg['no_trade_hours'])
m = base.reset_index()
m['day'] = m.time.dt.normalize()
m['hm'] = m.time.dt.hour * 100 + m.time.dt.minute
T = m.time.values
O, H, L, C, SP = (m[k].values for k in ('open', 'high', 'low', 'close', 'sp'))
HRS = m.time.dt.hour.values
TS = pd.DatetimeIndex(m.time)
bars_per_day_min = 100 if cfg['tf'] == 5 else 34

dm = m[(m.hm >= 100) & (m.hm <= 2255)]
d1 = dm.groupby('day').agg(open=('open', 'first'), high=('high', 'max'), low=('low', 'min'),
                           close=('close', 'last'), n=('close', 'size'))
d1 = d1[d1.n >= bars_per_day_min]
pc = d1.close.shift(1)
tr = pd.concat([d1.high - d1.low, (d1.high - pc).abs(), (d1.low - pc).abs()], axis=1).max(axis=1)
d1['atr_prev'] = tr.rolling(14).mean().shift(1)


def run(entry_i, direction, stop, exit_i):
    entry = O[entry_i]
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    for k in range(entry_i, exit_i + 1):
        if HRS[k] in NOTRADE:
            continue
        if direction > 0:
            if k > entry_i and O[k] <= stop:
                return (O[k] - entry) / risk, k, risk
            if L[k] <= stop:
                return -1.0, k, risk
        else:
            if k > entry_i and O[k] >= stop:
                return (entry - O[k]) / risk, k, risk
            if H[k] >= stop:
                return -1.0, k, risk
    return (C[exit_i] - entry) * direction / risk, exit_i, risk


def add(rows, serie, i, d, stop, j_exit):
    if pd.Timestamp(T[i]) < pd.Timestamp('2016-01-01'):
        return
    r = run(i, d, stop, j_exit)
    if r is None:
        return
    R, k, risk = r
    nights = (pd.Timestamp(T[k]).normalize() - pd.Timestamp(T[i]).normalize()).days
    cost2 = 2 * (SP[i] + swap_cost(cfg, d, O[i], nights)) / risk
    rows.append(dict(serie=serie, time=pd.Timestamp(T[i]), dir=d, entry=O[i], stop=stop, risk=risk,
                     exit_time=pd.Timestamp(T[k]), R_lordo=R, cost2=cost2, R=R - cost2))


def at(day, hm, after=True):
    ts = pd.Timestamp(day) + pd.Timedelta(hours=hm // 100, minutes=hm % 100)
    if after:
        k = TS.searchsorted(ts)
        return int(k) if k < len(TS) and TS[k] - ts <= pd.Timedelta(minutes=15) else None
    k = TS.searchsorted(ts, side='right') - 1
    return int(k) if k >= 0 and ts - TS[k] <= pd.Timedelta(minutes=30) else None


rows = []
days = list(d1.index)
for day in days:                                   # ---------- F ----------
    a, b, e, x = at(day, 1530), at(day, 1725, False), at(day, 1730), at(day, 2255, False)
    if None in (a, b, e, x) or not (a <= b < e <= x):
        continue
    mv = C[b] - O[a]
    if abs(mv) < 0.0025 * KT * O[a]:
        continue
    d = 1 if mv > 0 else -1
    lo, hi = L[a:b + 1].min(), H[a:b + 1].max()
    basep = lo if d > 0 else hi
    stop = O[e] - d * abs(O[e] - basep) * KS
    add(rows, 'F', e, d, stop, x)

ecb = pd.read_csv(ECB_PATH, usecols=['TIME_PERIOD', 'OBS_VALUE'])
ecb['day'] = pd.to_datetime(ecb.TIME_PERIOD)
ecb = ecb.dropna().set_index('day').OBS_VALUE.astype(float)
ecb_chg = ecb.pct_change()
for n, day in enumerate(days[:-1]):               # ---------- G ----------
    if day not in ecb_chg.index or np.isnan(ecb_chg[day]) or np.isnan(d1.atr_prev[day]):
        continue
    ch = ecb_chg[day]
    if abs(ch) < 0.005 * KT:
        continue
    e, x = at(day, 1700), at(days[n + 1], 1700)
    if e is None or x is None:
        continue
    d = 1 if ch > 0 else -1                        # EUR/USD: segue il cambio; Bitcoin: dollaro debole -> compra
    stop = O[e] - d * 1.5 * d1.atr_prev[day] * KS
    add(rows, 'G', e, d, stop, x - 1)

for n in range(1, len(days) - 1):                  # ---------- H ----------
    day, nxt = days[n], days[n + 1]
    atr = d1.atr_prev[day]
    if np.isnan(atr):
        continue
    mv = d1.close[day] - d1.close[days[n - 1]]
    if abs(mv) < 1.0 * KT * atr:
        continue
    e, x = at(nxt, 100), at(nxt, 2255, False)
    if e is None or x is None:
        continue
    d = -1 if mv > 0 else 1
    stop = O[e] - d * 1.0 * atr * KS
    add(rows, 'H', e, d, stop, x)

t = pd.DataFrame(rows)
tag = '' if (KT, KS) == (1.0, 1.0) else f'_soglia{KT}_stop{KS}'
print(f"{cfg['nome']} - fattore soglia {KT}, fattore stop {KS}")
for s, g in t.groupby('serie'):
    line, py, ok, st = summary(g, label=s)
    print(line)
    print('   per anno (costi doppi):', py)
if not tag:
    t.to_csv(f'../{MKT}/t6_FGH_operazioni.csv', index=False)
