"""Prova 1 - Serie C1 (candela avvolgente M15 a favore del trend H1) rifatta su EUR/USD o Bitcoin.
Stesse regole di 1_Bot/Scrematura_Python/screen_c1.py; unico adattamento (registrato nel Manuale prima del
calcolo): stop ammesso tra lo 0,1% e lo 0,4% del prezzo invece di 1,5-6 $. Esecuzione sulle candele base del
mercato (EUR/USD M15, Bitcoin M5). Costi doppi: 2 x costo per operazione del mercato (vedi mercati.py).
Uso: python3 t1_c1_avvolgente.py <EURUSD|BTC> [moltiplicatore_stop]
"""
import sys
import numpy as np
import pandas as pd
from mercati import load, resample, summary

MKT = sys.argv[1]
STOP_MULT = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
MIN_STOP, MAX_STOP = 0.001, 0.004

base, cfg = load(MKT, warmup_days=10)
m15 = resample(base, '15min')
h1 = resample(base, '1h')
h1['ema'] = h1.close.ewm(span=50, adjust=False).mean()
h1_known = pd.Series(np.sign(h1.close - h1.ema).values, index=h1.index + pd.Timedelta(hours=1))

o, c, hi, lo = m15.open, m15.close, m15.high, m15.low
po, pc = o.shift(1), c.shift(1)
bull = (pc < po) & (c > o) & (c >= po) & (o <= pc)
bear = (pc > po) & (c < o) & (c <= po) & (o >= pc)

bt = base.index.values
bh, bl, bo, bc = base.high.values, base.low.values, base.open.values, base.close.values
step = pd.Timedelta(minutes=cfg['tf'])
trades = []
busy_until = pd.Timestamp('2000-01-01')
idx = m15.index
for i in range(1, len(idx) - 1):
    sig_t = idx[i]
    ent_t = sig_t + pd.Timedelta(minutes=15)
    if sig_t < pd.Timestamp('2016-01-01') or idx[i + 1] != ent_t:
        continue
    hm = ent_t.hour * 60 + ent_t.minute
    if not (15 * 60 <= hm <= 18 * 60 + 45) or ent_t < busy_until:
        continue
    if not (bull.iloc[i] or bear.iloc[i]):
        continue
    known = h1_known[h1_known.index <= ent_t]
    if known.empty:
        continue
    d = 1 if bull.iloc[i] else -1
    if known.iloc[-1] != d:
        continue
    entry = m15.open.iloc[i + 1]
    basedist = entry - lo.iloc[i] if d > 0 else hi.iloc[i] - entry
    if not (MIN_STOP * entry <= basedist <= MAX_STOP * entry):
        continue
    dist = basedist * STOP_MULT
    stop, tgt = entry - d * dist, entry + d * dist
    exit_t = ent_t.normalize() + pd.Timedelta(hours=21, minutes=30)
    a = np.searchsorted(bt, np.datetime64(ent_t))
    b = np.searchsorted(bt, np.datetime64(exit_t))
    pnl = None
    for j in range(a, b):
        if d > 0:
            if bl[j] <= stop: pnl = -dist; break
            if bh[j] >= tgt: pnl = dist; break
        else:
            if bh[j] >= stop: pnl = -dist; break
            if bl[j] <= tgt: pnl = dist; break
    if pnl is None:
        if b >= len(bt) or pd.Timestamp(bt[b]).normalize() != ent_t.normalize():
            px = bc[b - 1]
        else:
            px = bo[b]
        pnl = (px - entry) * d
        end_t = exit_t
    else:
        end_t = pd.Timestamp(bt[j]) + step
    cost = 2 * base.sp.values[a]
    trades.append((ent_t, d, (pnl - cost) / dist, pnl / dist))
    busy_until = end_t

t = pd.DataFrame(trades, columns=['time', 'dir', 'R', 'R_lordo'])
line, py, ok, s = summary(t, label=f'C1 {MKT} stop x{STOP_MULT:g}')
print(line)
print('   per anno:', py)
if STOP_MULT == 1.0:
    t.to_csv(f'../{MKT}/t1_c1_operazioni.csv', index=False)
