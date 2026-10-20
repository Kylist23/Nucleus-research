"""Serie D, tentativo 1: obiettivo raddoppio (Progetto Nucleus).
Criteri registrati nel Manuale il 14/10/2026 PRIMA di eseguire questo script.
Regola: chiusura giornaliera sopra la media a 200 giorni -> comprati, sotto -> venduti.
Cambio all'apertura del giorno dopo. Valore della posizione = capitale x 25% / volatilita' annua (60 g),
massimo 3 x capitale, fissato all'entrata. Stop di emergenza al 40% di drawdown.
Capitale 10.000 EUR, profitti convertiti con il cambio BCE. Costi doppi: 2 x spread (min 0,20 $) per operazione,
2 x swap stimato (acquisti 3%/anno, vendite 1%/anno del valore: ipotesi da verificare nel tester).
Uso: python3 -I sim_d1_raddoppio.py <M5 broker csv> <stooq xauusd_d.csv> <BCE eur_usd csv> [costi: 2|1|0]
"""
import sys
import numpy as np
import pandas as pd

M5, STOOQ, ECB = sys.argv[1:4]
CM = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0       # moltiplicatore dei costi (2 = regola Nucleus)
CAP0, VOL_T, MAX_LEV, DD_STOP = 10_000.0, 0.25, 3.0, 0.40
SWAP_LONG, SWAP_SHORT, MIN_SP = 0.03, 0.01, 0.20

m5 = pd.read_csv(M5)
m5['time'] = pd.to_datetime(m5.time, format='%Y.%m.%d %H:%M')
m5 = m5[m5.time >= '2016-01-01']
m5['day'] = m5.time.dt.normalize()
m5['sp'] = m5.spread_points * 0.01
op = m5[m5.time.dt.hour >= 1].groupby('day').agg(open=('open', 'first'), sp_open=('sp', 'first'))
cl = m5[m5.time.dt.hour <= 22].groupby('day').agg(close=('close', 'last'))
d = op.join(cl, how='inner')

# riscaldamento di media e volatilita' con le chiusure Stooq del 2015 (solo per i calcoli, nessuna operazione)
st = pd.read_csv(STOOQ, parse_dates=['Date']).set_index('Date')
warm = st.loc['2014-06-01':'2015-12-31', 'Close']
closes = pd.concat([warm, d.close])
sma = closes.rolling(200).mean()
vol = np.log(closes).diff().rolling(60).std() * np.sqrt(252)
d['sig'] = np.sign(d.close - sma.reindex(d.index))
d['vol'] = vol.reindex(d.index)

fx = pd.read_csv(ECB, usecols=['TIME_PERIOD', 'OBS_VALUE'], parse_dates=['TIME_PERIOD'])
fx = fx.set_index('TIME_PERIOD').OBS_VALUE.astype(float)
d['eurusd'] = fx.reindex(d.index, method='ffill')

def run(rule='trend', lev=None):
    eq, peak, q, side, halted = CAP0, CAP0, 0.0, 0, False
    rows, trades = [], []
    idx = d.index
    for i in range(1, len(idx)):
        t, p = idx[i], idx[i - 1]
        o, rate = d.open.iloc[i], d.eurusd.iloc[i]
        # 1) profitto dall'apertura di ieri a quella di oggi + swap delle notti trascorse
        if q:
            pnl_usd = side * q * (o - d.open.iloc[i - 1])
            nights = (t - p).days
            sw = (SWAP_LONG if side > 0 else SWAP_SHORT) * CM * q * d.open.iloc[i - 1] * nights / 365
            eq += (pnl_usd - sw) / rate
            trades[-1]['net'] += (pnl_usd - sw) / rate
        peak = max(peak, eq)
        if not halted and eq <= peak * (1 - DD_STOP):
            halted, q, side = True, 0.0, 0
        # 2) decisione presa con la chiusura di ieri, eseguita all'apertura di oggi
        want = (1 if i == 1 else side) if rule == 'hold' else d.sig.iloc[i - 1]
        if not halted and want != side and not np.isnan(want) and want != 0:
            if rule == 'hold':
                notional_usd = lev * eq * rate
            else:
                v = d.vol.iloc[i - 1]
                notional_usd = min(VOL_T / v, MAX_LEV) * eq * rate
            q, side = notional_usd / o, int(want)
            cost = CM * max(d.sp_open.iloc[i], MIN_SP) * q / rate
            eq -= cost
            trades.append(dict(time=t, dir=side, net=-cost))
        rows.append((t, eq))
    curve = pd.Series(dict(rows))
    tr = pd.DataFrame(trades)
    return curve, tr

def report(name, curve, tr):
    dd = (curve / curve.cummax() - 1).min()
    print(f"{name}: finale {curve.iloc[-1]:,.0f} EUR ({curve.iloc[-1] / CAP0:.2f}x) | drawdown massimo {dd:.1%} | operazioni {len(tr)}")
    if len(tr) and tr.dir.nunique() > 1 or (len(tr) and name.startswith('TREND')):
        tr['y'] = tr.time.dt.year
        print(f"   acquisti {tr[tr.dir > 0].net.sum():+,.0f} EUR ({(tr.dir > 0).sum()}) | vendite {tr[tr.dir < 0].net.sum():+,.0f} EUR ({(tr.dir < 0).sum()})")
        yr = curve.groupby(curve.index.year).last()
        start = pd.concat([pd.Series({2015: CAP0}), yr]).shift(1).dropna()
        print('   rendimento per anno:', {int(k): f"{(yr[k] / start[k] - 1):+.0%}" for k in yr.index})
        print(f"   2016-2019 {yr[2019] - CAP0:+,.0f} EUR | 2020-2022 {yr[2022] - yr[2019]:+,.0f} EUR")
    return curve

print(f"Costi x{CM:g}. Oro: apertura {d.open.iloc[0]:.2f} $ il {d.index[0].date()}, chiusura {d.close.iloc[-1]:.2f} $ il {d.index[-1].date()}")
c_tr, t_tr = run('trend')
report('TREND 200 giorni, volatilita 25%', c_tr, t_tr)
c_bh, t_bh = run('hold', 1.0)
report('Compra e tieni, leva 1', c_bh, t_bh)
for lev in [1.5, 2.0, 3.0]:
    c, t = run('hold', lev)
    report(f'Compra e tieni, leva {lev:g}', c, t)
if '--salva' in sys.argv:
    pd.DataFrame({'trend': c_tr, 'compra_tieni_1x': c_bh}).to_csv('sim_d1_curve.csv')
    t_tr.to_csv('sim_d1_operazioni.csv', index=False)
