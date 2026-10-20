"""Scrematura delle idee candidate per B3 (Progetto Nucleus).
Criteri fissati PRIMA di eseguire (09/10/2026), in multipli di rischio R
(1R = distanza dello stop), con lo spread pagato DUE volte:
  1. almeno 100 operazioni
  2. somma R positiva
  3. acquisti e vendite entrambi positivi
  4. 2016-2019 e 2020-2022 entrambi positivi
Dati: XAUUSD M5 del broker, 2016-2022 (cassaforte 2023+ intatta).
Orario operativo: 01:00-22:59 server (dopo le 23:00 il broker non esegue).
"""
import pandas as pd, numpy as np, sys

df = pd.read_csv(sys.argv[1])
df['time'] = pd.to_datetime(df['time'], format='%Y.%m.%d %H:%M')
df = df[(df.time >= '2016-01-01') & (df.time.dt.hour >= 1) & (df.time.dt.hour <= 22)].reset_index(drop=True)
df['sp'] = df.spread_points * 0.01          # spread in dollari
df['day'] = df.time.dt.normalize()
COST_MULT = 2.0

def report(name, tr):
    t = pd.DataFrame(tr, columns=['time', 'dir', 'R'])
    if t.empty: print(name, 'nessuna operazione'); return
    t['y'] = t.time.dt.year
    L, S = t[t.dir > 0].R.sum(), t[t.dir < 0].R.sum()
    p1, p2 = t[t.y <= 2019].R.sum(), t[t.y >= 2020].R.sum()
    ok = [len(t) >= 100, t.R.sum() > 0, L > 0 and S > 0, p1 > 0 and p2 > 0]
    print(f"{name}: n={len(t)} totale={t.R.sum():+.1f}R acquisti={L:+.1f}R vendite={S:+.1f}R "
          f"2016-19={p1:+.1f}R 2020-22={p2:+.1f}R | criteri {['OK' if o else 'NO' for o in ok]} -> "
          f"{'PASSA' if all(ok) else 'bocciata'}")
    print('   per anno:', t.groupby('y').R.sum().round(1).to_dict())

# ---------- Giornaliero dalle M5 ----------
d = df.groupby('day').agg(open=('open', 'first'), high=('high', 'max'), low=('low', 'min'),
                          close=('close', 'last'), sp=('sp', 'median')).reset_index()
tr = pd.concat([d.high - d.low, (d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()], axis=1).max(axis=1)
d['atr'] = tr.rolling(14).mean()

# ---------- Idea 1: inversione dopo 3 chiusure giornaliere nella stessa direzione ----------
def idea1():
    out = []; i = 20
    c = d.close.values
    while i < len(d) - 1:
        up3 = c[i] > c[i-1] > c[i-2] > c[i-3]
        dn3 = c[i] < c[i-1] < c[i-2] < c[i-3]
        if not (up3 or dn3) or np.isnan(d.atr[i]): i += 1; continue
        dr = 1 if dn3 else -1
        e = d.open[i+1]; stop = d.atr[i]; cost = d.sp[i+1] * COST_MULT
        j = i + 1; pnl = None
        while j < len(d) and j <= i + 5:
            if dr > 0 and d.low[j] <= e - stop: pnl = -stop; break
            if dr < 0 and d.high[j] >= e + stop: pnl = -stop; break
            prev = c[j-1]
            if (dr > 0 and c[j] > prev) or (dr < 0 and c[j] < prev) or j == i + 5:
                pnl = (c[j] - e) * dr; break
            j += 1
        if pnl is None: break
        out.append((d.day[i+1], dr, (pnl - cost) / stop)); i = j
    return out

# ---------- Idea 2: rottura del range asiatico (01-10) tra le 10 e le 22 ----------
def idea2():
    out = []
    for day, g in df.groupby('day'):
        a = g[g.time.dt.hour < 10]; s = g[g.time.dt.hour >= 10]
        if len(a) < 60 or len(s) < 60: continue
        hi, lo = a.high.max(), a.low.min()
        if hi <= lo: continue
        sv = s.reset_index(drop=True)
        for k in range(len(sv) - 1):
            dr = 1 if sv.close[k] > hi else (-1 if sv.close[k] < lo else 0)
            if dr == 0: continue
            e = sv.open[k+1]; stop = abs(e - (lo if dr > 0 else hi))
            if stop <= 0: break
            cost = sv.sp[k+1] * COST_MULT; pnl = None
            for m in range(k + 1, len(sv)):
                if dr > 0 and sv.low[m] <= e - stop: pnl = -stop; break
                if dr < 0 and sv.high[m] >= e + stop: pnl = -stop; break
            if pnl is None: pnl = (sv.close.iloc[-1] - e) * dr
            out.append((day, dr, (pnl - cost) / stop)); break
    return out

# ---------- Idea 3: ritorno alla media su H1 (Bollinger 20, 2.5) ----------
def idea3():
    h = df.set_index('time').resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min',
                                                 'close': 'last', 'sp': 'median'}).dropna().reset_index()
    h['ma'] = h.close.rolling(20).mean(); h['sd'] = h.close.rolling(20).std()
    trh = pd.concat([h.high - h.low, (h.high - h.close.shift()).abs(), (h.low - h.close.shift()).abs()], axis=1).max(axis=1)
    h['atr'] = trh.rolling(14).mean()
    out = []; i = 30
    while i < len(h) - 1:
        if np.isnan(h.atr[i]) or h.time[i].hour >= 21: i += 1; continue
        dr = -1 if h.close[i] > h.ma[i] + 2.5 * h.sd[i] else (1 if h.close[i] < h.ma[i] - 2.5 * h.sd[i] else 0)
        if dr == 0: i += 1; continue
        e = h.open[i+1]; stop = h.atr[i]; cost = h.sp[i+1] * COST_MULT; day = h.time[i+1].normalize()
        j = i + 1; pnl = None
        while j < len(h):
            if dr > 0 and h.low[j] <= e - stop: pnl = -stop; break
            if dr < 0 and h.high[j] >= e + stop: pnl = -stop; break
            back = (dr > 0 and h.close[j] >= h.ma[j]) or (dr < 0 and h.close[j] <= h.ma[j])
            if back or h.time[j].hour >= 22 or h.time[j].normalize() != day:
                pnl = (h.close[j] - e) * dr; break
            j += 1
        if pnl is None: break
        out.append((h.time[i+1], dr, (pnl - cost) / stop)); i = j + 1
    return out

report('Idea 1 - inversione dopo 3 giorni (D1)', idea1())
report('Idea 2 - rottura range asiatico', idea2())
report('Idea 3 - ritorno alla media H1', idea3())
