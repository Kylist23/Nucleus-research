"""Scrematura Serie C, tentativo 1 (Progetto Nucleus) - candela avvolgente a favore del trend.
Criteri registrati nel Manuale il 14/10/2026 PRIMA di eseguire questo script.
Regola: M15; entrata all'apertura della candela M15 dopo un'avvolgente, apertura tra 15:00 e 18:45 server;
trend = ultima chiusura H1 completata contro la sua EMA 50; stop al minimo/massimo dell'avvolgente;
target 1R; stop tra 1,5 e 6 $; uscita forzata 21:30; una posizione alla volta.
Costo per operazione = 2 x max(spread, 0,20 $). Stop e target nella stessa candela M5: conta lo stop.
Uso: python3 -I screen_c1.py ../Dati/XAUUSD_M5_2016-2022.csv [moltiplicatore_stop]
"""
import sys
import numpy as np
import pandas as pd

STOP_MULT = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
MIN_STOP, MAX_STOP = 1.5, 6.0
MIN_SPREAD = 0.20

m5 = pd.read_csv(sys.argv[1])
m5['time'] = pd.to_datetime(m5['time'], format='%Y.%m.%d %H:%M')
m5 = m5[m5.time >= '2016-01-01'].set_index('time').sort_index()
m5['sp'] = m5.spread_points * 0.01

agg = dict(open='first', high='max', low='min', close='last', sp='median')
m15 = m5.resample('15min', label='left', closed='left').agg(agg).dropna(subset=['open'])
h1 = m5.resample('1h', label='left', closed='left').agg(agg).dropna(subset=['open'])
h1['ema'] = h1.close.ewm(span=50, adjust=False).mean()
# trend noto alla fine dell'ora: la barra H1 che inizia alle 14:00 e' completa alle 15:00
h1_known = pd.Series(np.sign(h1.close - h1.ema).values, index=h1.index + pd.Timedelta(hours=1))

o, c, hi, lo = m15.open, m15.close, m15.high, m15.low
po, pc = o.shift(1), c.shift(1)
bull = (pc < po) & (c > o) & (c >= po) & (o <= pc)
bear = (pc > po) & (c < o) & (c <= po) & (o >= pc)

m5_t = m5.index.values
m5_h, m5_l, m5_o = m5.high.values, m5.low.values, m5.open.values

trades = []
busy_until = pd.Timestamp('2000-01-01')
idx = m15.index
for i in range(1, len(idx) - 1):
    sig_t = idx[i]
    ent_t = sig_t + pd.Timedelta(minutes=15)
    if idx[i + 1] != ent_t:            # la candela successiva deve essere contigua (niente buchi o fine settimana)
        continue
    hm = ent_t.hour * 60 + ent_t.minute
    if not (15 * 60 <= hm <= 18 * 60 + 45) or ent_t < busy_until:
        continue
    if not (bull.iloc[i] or bear.iloc[i]):
        continue
    # trend: ultima H1 completata all'istante di entrata
    known = h1_known[h1_known.index <= ent_t]
    if known.empty:
        continue
    trend = known.iloc[-1]
    d = 1 if bull.iloc[i] else -1
    if trend != d:
        continue
    entry = m15.open.iloc[i + 1]
    base = entry - lo.iloc[i] if d > 0 else hi.iloc[i] - entry
    if not (MIN_STOP <= base <= MAX_STOP):
        continue
    dist = base * STOP_MULT
    stop, tgt = entry - d * dist, entry + d * dist
    exit_t = ent_t.normalize() + pd.Timedelta(hours=21, minutes=30)
    a = np.searchsorted(m5_t, np.datetime64(ent_t))
    b = np.searchsorted(m5_t, np.datetime64(exit_t))
    pnl = None
    for j in range(a, b):
        if d > 0:
            if m5_l[j] <= stop: pnl = -dist; break
            if m5_h[j] >= tgt: pnl = dist; break
        else:
            if m5_h[j] >= stop: pnl = -dist; break
            if m5_l[j] <= tgt: pnl = dist; break
    if pnl is None:
        if b >= len(m5_t) or pd.Timestamp(m5_t[b]).normalize() != ent_t.normalize():
            last = b - 1            # nessuna candela alle 21:30: chiusura all'ultima disponibile
            px = m5.close.values[last]
        else:
            px = m5_o[b]
        pnl = (px - entry) * d
        end_t = exit_t
    else:
        end_t = pd.Timestamp(m5_t[j]) + pd.Timedelta(minutes=5)
    sp = max(m15.sp.iloc[i + 1], MIN_SPREAD)
    cost = 2 * sp
    trades.append((ent_t, d, (pnl - cost) / dist, pnl / dist))
    busy_until = end_t

t = pd.DataFrame(trades, columns=['time', 'dir', 'R', 'R_lordo'])
t['y'] = t.time.dt.year
L, S = t[t.dir > 0].R.sum(), t[t.dir < 0].R.sum()
p1, p2 = t[t.y <= 2019].R.sum(), t[t.y >= 2020].R.sum()
last3 = t[t.time >= '2020-09-01'].R.sum()
ok = [len(t) >= 100, t.R.sum() > 0, L > 0 and S > 0, p1 > 0 and p2 > 0]
cum = t.R.cumsum()
print(f"stop x{STOP_MULT}: n={len(t)} vinte={(t.R_lordo > 0).mean():.1%} totale={t.R.sum():+.1f}R (senza costi {t.R_lordo.sum():+.1f}R) "
      f"acquisti={L:+.1f}R vendite={S:+.1f}R 2016-19={p1:+.1f}R 2020-22={p2:+.1f}R ultimo terzo={last3:+.1f}R "
      f"perdita massima={(cum - cum.cummax()).min():.1f}R")
print('   per anno:', t.groupby('y').R.sum().round(1).to_dict())
print('   criteri', ['OK' if x else 'NO' for x in ok], '->', 'PASSA' if all(ok) else 'BOCCIATA')
