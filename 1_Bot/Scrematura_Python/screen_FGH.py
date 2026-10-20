"""Scrematura Serie F, G, H, tentativo 1 (criteri nel Manuale, capitolo 8, registrati il 20/10/2026).
F: continuazione del movimento 15:30-17:25 server (dati USA). G: oro dopo un forte movimento dell'EUR/USD BCE.
H: rimbalzo il giorno dopo un movimento di almeno 1 ATR(14) giornaliero.
Correzione di esecuzione (20/10/2026, non e' un nuovo tentativo): quasi tutti i giorni la prima candela M5
e' delle 01:05 e in circa 150 giorni manca quella delle 22:55; si usa la prima candela entro 15 minuti dopo
l'orario di entrata e l'ultima entro 30 minuti prima dell'orario di uscita.
Uso: python3 -I screen_FGH.py <XAUUSD_M5.csv> <eur_usd_ecb_raw.csv> [fattore_soglia fattore_stop]
I due fattori (predefiniti 1,0) servono solo per le prove di robustezza.
"""
import sys
import numpy as np
import pandas as pd

M5_PATH, ECB_PATH = sys.argv[1], sys.argv[2]
KT = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
KS = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0

m5 = pd.read_csv(M5_PATH)
m5['time'] = pd.to_datetime(m5['time'], format='%Y.%m.%d %H:%M')
m5 = m5[(m5.time >= '2016-01-01') & (m5.time < '2023-01-01')].sort_values('time').reset_index(drop=True)
m5['sp'] = m5.spread_points * 0.01
m5['day'] = m5.time.dt.normalize()
m5['hm'] = m5.time.dt.hour * 100 + m5.time.dt.minute
T = m5.time.values
O, H, L, C, SP = (m5[k].values for k in ('open', 'high', 'low', 'close', 'sp'))
HM = m5.hm.values
idx_of = pd.Series(np.arange(len(m5)), index=m5.time)

# giornata del broker 01:00-22:55, ATR(14) giornaliero calcolato fino al giorno prima
dm = m5[(m5.hm >= 100) & (m5.hm <= 2255)]
d1 = dm.groupby('day').agg(open=('open', 'first'), high=('high', 'max'), low=('low', 'min'),
                           close=('close', 'last'), n=('close', 'size'))
d1 = d1[d1.n >= 100]
pc = d1.close.shift(1)
tr = pd.concat([d1.high - d1.low, (d1.high - pc).abs(), (d1.low - pc).abs()], axis=1).max(axis=1)
d1['atr_prev'] = tr.rolling(14).mean().shift(1)


def run(entry_i, direction, stop, exit_i):
    """Simula un'operazione da entry_i (apertura) fino a exit_i (incluso). Restituisce R lordo, uscita."""
    entry = O[entry_i]
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    for k in range(entry_i, exit_i + 1):
        if HM[k] >= 2300 or HM[k] < 100:
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
    r = run(i, d, stop, j_exit)
    if r is None:
        return
    R, k, risk = r
    nights = (pd.Timestamp(T[k]).normalize() - pd.Timestamp(T[i]).normalize()).days
    swap = (0.03 if d > 0 else 0.01) * O[i] * nights / 365
    cost2 = 2 * (max(SP[i], 0.20) + swap) / risk
    rows.append(dict(serie=serie, time=pd.Timestamp(T[i]), dir=d, entry=O[i], stop=stop, risk=risk,
                     exit_time=pd.Timestamp(T[k]), R=R, cost2=cost2, R_net2=R - cost2))


TS = pd.DatetimeIndex(m5.time)


def at(day, hm, after=True):
    """Candela M5 all'orario hm; se manca, la prima entro 15 minuti dopo (after) o l'ultima entro 30 prima."""
    ts = pd.Timestamp(day) + pd.Timedelta(hours=hm // 100, minutes=hm % 100)
    if after:
        k = TS.searchsorted(ts)
        return int(k) if k < len(TS) and TS[k] - ts <= pd.Timedelta(minutes=15) else None
    k = TS.searchsorted(ts, side='right') - 1
    return int(k) if k >= 0 and ts - TS[k] <= pd.Timedelta(minutes=30) else None


rows = []
days = list(d1.index)
# ---------- F ----------
for day in days:
    a, b, e, x = at(day, 1530), at(day, 1725, False), at(day, 1730), at(day, 2255, False)
    if None in (a, b, e, x):
        continue
    mv = C[b] - O[a]
    if abs(mv) < 0.0025 * KT * O[a]:
        continue
    d = 1 if mv > 0 else -1
    lo, hi = L[a:b + 1].min(), H[a:b + 1].max()
    base = lo if d > 0 else hi
    stop = O[e] - d * abs(O[e] - base) * KS
    add(rows, 'F', e, d, stop, x)

# ---------- G ----------
ecb = pd.read_csv(ECB_PATH, usecols=['TIME_PERIOD', 'OBS_VALUE'])
ecb['day'] = pd.to_datetime(ecb.TIME_PERIOD)
ecb = ecb.dropna().set_index('day').OBS_VALUE.astype(float)
ecb_chg = ecb.pct_change()
for n, day in enumerate(days[:-1]):
    if day not in ecb_chg.index or np.isnan(ecb_chg[day]) or np.isnan(d1.atr_prev[day]):
        continue
    ch = ecb_chg[day]
    if abs(ch) < 0.005 * KT:
        continue
    e, x = at(day, 1700), at(days[n + 1], 1700)
    if e is None or x is None:
        continue
    d = 1 if ch > 0 else -1
    stop = O[e] - d * 1.5 * d1.atr_prev[day] * KS
    add(rows, 'G', e, d, stop, x - 1)
# correlazione descrittiva nello stesso giorno (oro alle 17:00 server, EUR/USD BCE)
g17 = pd.Series({day: O[at(day, 1700)] for day in days if at(day, 1700) is not None})
both = pd.concat([g17.pct_change(), ecb_chg], axis=1, join='inner').dropna()
corr_same = both.corr().iloc[0, 1]

# ---------- H ----------
for n in range(1, len(days) - 1):
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
t['y'] = t.time.dt.year
tag = '' if (KT, KS) == (1.0, 1.0) else f'_soglia{KT}_stop{KS}'
t.to_csv(f'screen_FGH_operazioni{tag}.csv', index=False)
print(f'fattore soglia {KT}, fattore stop {KS}')
for s, g in t.groupby('serie'):
    eq = (1 + 0.005 * g.R_net2).cumprod()
    dd = (1 - eq / eq.cummax()).max() * 100
    L_, S_ = g.R_net2[g.dir > 0].sum(), g.R_net2[g.dir < 0].sum()
    p1, p2 = g.R_net2[g.y <= 2019].sum(), g.R_net2[g.y >= 2020].sum()
    last = g.R_net2[g.time >= '2020-09-01'].sum()
    ok = [len(g) >= 100, g.R_net2.sum() > 0, L_ > 0 and S_ > 0, p1 > 0 and p2 > 0, dd < 10]
    print(f"{s}: operazioni={len(g)} (acq {int((g.dir > 0).sum())}, ven {int((g.dir < 0).sum())}) "
          f"lordo={g.R.sum():+.1f}R costi_doppi={g.R_net2.sum():+.1f}R media={g.R_net2.mean():+.3f}R "
          f"vinte={(g.R_net2 > 0).mean():.0%} acquisti={L_:+.1f}R vendite={S_:+.1f}R "
          f"2016-19={p1:+.1f}R 2020-22={p2:+.1f}R ultimo_terzo={last:+.1f}R dd={dd:.1f}% "
          f"criteri={''.join('S' if c else 'N' for c in ok)}")
    print('   per anno (costi doppi):', g.R_net2.groupby(g.y).sum().round(1).to_dict())
print(f'G, correlazione nello stesso giorno tra variazione oro (17:00 server) e EUR/USD BCE: {corr_same:+.2f} '
      f'su {len(both)} giorni')
