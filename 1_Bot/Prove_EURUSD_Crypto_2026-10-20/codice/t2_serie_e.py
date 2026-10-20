"""Prova 2 - Serie E (rottura delle 24 ore H1; E1 trailing, E2 a fette, CTRL target 2R) su EUR/USD o Bitcoin.
Stesse regole di 1_Bot/Scrematura_Python/screen_e.py; esecuzione sulle candele base del mercato (EUR/USD M15,
Bitcoin M5); costi e ore senza esecuzione da mercati.py.
Uso: python3 t2_serie_e.py <EURUSD|BTC> <E1|E2|CTRL> [moltiplicatore stop/trailing] [costi: 2|1|0]
"""
import sys
import numpy as np
import pandas as pd
from mercati import load, resample, summary, swap_cost

MKT, MODE = sys.argv[1], sys.argv[2]
MULT = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
CM = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
STOP_ATR, TRAIL_ATR = 2.0 * MULT, 2.5 * MULT
CHANNEL, ATR_N = 24, 14
TRANCHES = [(2.0, 0.25, 0.0), (3.0, 0.25, 2.0), (5.0, 0.25, 3.0)]

base, cfg = load(MKT, warmup_days=10)
NOTRADE = set(cfg['no_trade_hours'])
h1 = resample(base, '1h')
pc = h1.close.shift(1)
tr = pd.concat([h1.high - h1.low, (h1.high - pc).abs(), (h1.low - pc).abs()], axis=1).max(axis=1)
h1['atr'] = tr.rolling(ATR_N).mean()
hi_ch = h1.high.rolling(CHANNEL).max().shift(1)
lo_ch = h1.low.rolling(CHANNEL).min().shift(1)
up, dn = h1.close > hi_ch, h1.close < lo_ch
h1['sig'] = np.where(up & ~up.shift(1, fill_value=False), 1, np.where(dn & ~dn.shift(1, fill_value=False), -1, 0))

T = base.index.values
O, H, L, C, SP = (base[c].values for c in ('open', 'high', 'low', 'close', 'sp'))
HR = base.index.hour.values
h1_close, h1_atr = h1.close, h1.atr


def run_trade(a, d, entry, dist):
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
        if MODE in ('E1', 'E2') and j > a:
            done = t.floor('h') - pd.Timedelta(hours=1)
            if done >= ent_hour and done != last_h and done in h1_close.index:
                last_h = done
                cl, at = h1_close[done], h1_atr[done]
                best = max(best, cl) if d > 0 else min(best, cl)
                if MODE == 'E1' or tranche >= len(TRANCHES):
                    cand = best - d * TRAIL_ATR * at
                    stop = max(stop, cand) if d > 0 else min(stop, cand)
        if HR[j] in NOTRADE:
            continue
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
            if moved and ((L[j] if d > 0 else H[j]) - stop) * d <= 0:
                close_part(left, stop, j); return j, gross, nights_w
    j = len(T) - 1
    close_part(left, C[j], j)
    return j, gross, nights_w


trades = []
free_from = 0
for t_sig, row in h1[(h1.sig != 0) & (h1.index >= '2016-01-01')].iterrows():
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
    net = gross - CM * (SP[a] + swap_cost(cfg, d, entry, nights_w)) / dist
    trades.append((ta, d, net, gross, pd.Timestamp(T[j]), nights_w))
    free_from = j + 1

t = pd.DataFrame(trades, columns=['time', 'dir', 'R', 'R_lordo', 'uscita', 'notti'])
line, py, ok, s = summary(t, label=f'{MODE} {MKT} x{MULT:g} costi x{CM:g}')
print(line + f' notti_medie={t.notti.mean():.1f}')
print('   per anno:', py)
if MULT == 1.0 and CM == 2.0:
    t.to_csv(f'../{MKT}/t2_serie_{MODE}_operazioni.csv', index=False)
