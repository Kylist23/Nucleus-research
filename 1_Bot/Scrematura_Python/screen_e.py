"""Scrematura Serie E (Progetto Nucleus) - uscite della skill exit-strategies (agiprolabs, commit 981e1d7) sull'oro.
Criteri registrati nel Manuale il 20/10/2026 PRIMA di eseguire questo script.
Entrata comune: chiusura H1 oltre il massimo/minimo delle 24 H1 precedenti (solo rotture nuove), entrata
all'apertura della prima M5 dopo la chiusura, tra 02:00 e 21:59 server; stop iniziale 2 x ATR(14) H1.
  E1 = trailing: chiusura piu' favorevole dall'entrata - 2,5 x ATR(14) H1, aggiornato a ogni chiusura H1.
  E2 = a fette: 25% a 2R, 3R, 5R; stop a 0R, +2R, +3R dopo ogni fetta; ultimo 25% con il trailing di E1.
  CTRL = controllo: target fisso 2R (non giudicato).
Costi doppi: 2 x max(spread, 0,20 $) + 2 x swap stimato (acquisti 3%/anno, vendite 1%/anno, notti di calendario).
Stop e target nella stessa M5: conta lo stop. Nessuna esecuzione 23:00-00:59 server.
Uso: python3 -I screen_e.py ../Dati/XAUUSD_M5_2016-2022.csv <E1|E2|CTRL> [moltiplicatore stop/trailing] [costi: 2|1|0]
"""
import sys
import numpy as np
import pandas as pd

MODE = sys.argv[2]
MULT = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
CM = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
STOP_ATR, TRAIL_ATR = 2.0 * MULT, 2.5 * MULT
CHANNEL, ATR_N = 24, 14
MIN_SPREAD, SWAP_LONG, SWAP_SHORT = 0.20, 0.03, 0.01
TRANCHES = [(2.0, 0.25, 0.0), (3.0, 0.25, 2.0), (5.0, 0.25, 3.0)]   # (target R, quota, nuovo stop in R)

m5 = pd.read_csv(sys.argv[1])
m5['time'] = pd.to_datetime(m5['time'], format='%Y.%m.%d %H:%M')
m5 = m5[m5.time >= '2016-01-01'].set_index('time').sort_index()
m5['sp'] = m5.spread_points * 0.01

h1 = m5.resample('1h', label='left', closed='left').agg(
    dict(open='first', high='max', low='min', close='last')).dropna(subset=['open'])
pc = h1.close.shift(1)
tr = pd.concat([h1.high - h1.low, (h1.high - pc).abs(), (h1.low - pc).abs()], axis=1).max(axis=1)
h1['atr'] = tr.rolling(ATR_N).mean()
hi_ch = h1.high.rolling(CHANNEL).max().shift(1)
lo_ch = h1.low.rolling(CHANNEL).min().shift(1)
up, dn = h1.close > hi_ch, h1.close < lo_ch
h1['sig'] = np.where(up & ~up.shift(1, fill_value=False), 1, np.where(dn & ~dn.shift(1, fill_value=False), -1, 0))

T = m5.index.values
O, H, L, C, SP = (m5[c].values for c in ('open', 'high', 'low', 'close', 'sp'))
HR = m5.index.hour.values
h1_close = h1.close
h1_atr = h1.atr


def run_trade(a, d, entry, dist):
    """Simula una posizione da M5 indice a. Ritorna (indice uscita, R lordo, notti pesate per quota)."""
    stop = entry - d * dist
    tgt2 = entry + d * 2 * dist
    left, gross, nights_w = 1.0, 0.0, 0.0
    tranche = 0
    best = entry
    ent_day = pd.Timestamp(T[a]).normalize()
    ent_hour = pd.Timestamp(T[a]).floor('h')
    last_h = None

    def close_part(q, px, j):
        nonlocal left, gross, nights_w
        gross += q * (px - entry) * d / dist
        nights_w += q * (pd.Timestamp(T[j]).normalize() - ent_day).days
        left -= q

    for j in range(a, len(T)):
        t = pd.Timestamp(T[j])
        # aggiornamento del trailing con l'ultima H1 completata (iniziata dopo o insieme all'entrata)
        if MODE in ('E1', 'E2') and j > a:
            done = t.floor('h') - pd.Timedelta(hours=1)
            if done >= ent_hour and done != last_h and done in h1_close.index:
                last_h = done
                cl, at = h1_close[done], h1_atr[done]
                best = max(best, cl) if d > 0 else min(best, cl)
                if MODE == 'E1' or tranche >= len(TRANCHES):
                    cand = best - d * TRAIL_ATR * at
                    stop = max(stop, cand) if d > 0 else min(stop, cand)
        if HR[j] in (23, 0):
            continue
        # stop: apertura oltre lo stop, poi minimo/massimo della candela
        if (O[j] - stop) * d <= 0:
            close_part(left, O[j], j); return j, gross, nights_w
        if ((L[j] if d > 0 else H[j]) - stop) * d <= 0:
            close_part(left, stop, j); return j, gross, nights_w
        if MODE == 'CTRL':
            if ((H[j] if d > 0 else L[j]) - tgt2) * d >= 0:
                close_part(left, tgt2, j); return j, gross, nights_w
        elif MODE == 'E2':
            moved = False
            while tranche < len(TRANCHES):
                r, q, new_stop_r = TRANCHES[tranche]
                lvl = entry + d * r * dist
                if ((H[j] if d > 0 else L[j]) - lvl) * d < 0:
                    break
                close_part(q, lvl, j)
                ns = entry + d * new_stop_r * dist
                stop = max(stop, ns) if d > 0 else min(stop, ns)
                tranche += 1
                moved = True
            # prudenza: se nella stessa candela il prezzo ha toccato anche il nuovo stop, si esce
            if moved and ((L[j] if d > 0 else H[j]) - stop) * d <= 0:
                close_part(left, stop, j); return j, gross, nights_w
    j = len(T) - 1
    close_part(left, C[j], j)
    return j, gross, nights_w


trades = []
free_from = 0
for t_sig, row in h1[h1.sig != 0].iterrows():
    if np.isnan(row.atr):
        continue
    known = t_sig + pd.Timedelta(hours=1)
    a = np.searchsorted(T, np.datetime64(known))
    if a >= len(T) or a < free_from:
        continue
    ta = pd.Timestamp(T[a])
    if ta - known >= pd.Timedelta(hours=1) or not (2 <= ta.hour <= 21):
        continue
    d = int(row.sig)
    entry = O[a]
    dist = STOP_ATR * row.atr
    j, gross, nights_w = run_trade(a, d, entry, dist)
    spread_cost = CM * max(SP[a], MIN_SPREAD)
    swap_cost = CM * (SWAP_LONG if d > 0 else SWAP_SHORT) * entry * nights_w / 365
    net = gross - (spread_cost + swap_cost) / dist
    trades.append((ta, d, net, gross, pd.Timestamp(T[j]), nights_w))
    free_from = j + 1

t = pd.DataFrame(trades, columns=['time', 'dir', 'R', 'R_lordo', 'uscita', 'notti'])
t['y'] = t.time.dt.year
Lg, Sh = t[t.dir > 0].R.sum(), t[t.dir < 0].R.sum()
p1, p2 = t[t.y <= 2019].R.sum(), t[t.y >= 2020].R.sum()
last3 = t[t.time >= '2020-09-01'].R.sum()
eq = (1 + 0.005 * t.R).cumprod()
dd = (1 - eq / eq.cummax()).max()
ok = [len(t) >= 100, t.R.sum() > 0, Lg > 0 and Sh > 0, p1 > 0 and p2 > 0, dd < 0.10]
print(f"{MODE} x{MULT:g} costi x{CM:g}: n={len(t)} vinte={(t.R > 0).mean():.1%} totale={t.R.sum():+.1f}R "
      f"(senza costi {t.R_lordo.sum():+.1f}R) acquisti={Lg:+.1f}R vendite={Sh:+.1f}R "
      f"2016-19={p1:+.1f}R 2020-22={p2:+.1f}R ultimo terzo={last3:+.1f}R drawdown={dd:.1%} "
      f"notti medie={t.notti.mean():.1f} R medio={t.R.mean():+.3f} R migliore={t.R.max():+.1f}")
print('   per anno:', t.groupby('y').R.sum().round(1).to_dict())
print('   criteri', ['OK' if x else 'NO' for x in ok], '->', 'PASSA' if all(ok) else 'BOCCIATA')
if len(sys.argv) > 5:
    t.to_csv(sys.argv[5], index=False)
