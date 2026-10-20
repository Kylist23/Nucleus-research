"""Prova esplorativa (non e' un tentativo Nucleus): tre strategie "futures" di freqtrade-strategies
(github.com/freqtrade/freqtrade-strategies, cartella user_data/strategies/futures, commit f3340ce, licenza GPL-3),
che comprano E vendono allo scoperto. Freqtrade e TA-Lib non sono installati: le regole sono ricopiate in pandas,
riga per riga, con i valori predefiniti delle strategie. Nessun collegamento a exchange, nessun ordine.

  FAdxSmaStrategy (H1): entra se ADX(14) > 30 e la media semplice 12 incrocia la 48 (sopra = acquisto,
      sotto = vendita); esce quando ADX < 30; stop -5%; ROI {0: 5%, 30 min: 10%, 60 min: 7,5%}.
  VolatilitySystem (candele da 3 ore): acquisto se la variazione della chiusura supera 2 x ATR(14) della
      candela prima, vendita se scende di piu'; il segnale opposto chiude e rigira. Leva 1 (l'originale usa 2
      e raddoppia la posizione: tolti per confrontare alla pari).
  TrendFollowingStrategy (M5): acquisto quando la chiusura incrocia sopra l'EMA 20 e l'OBV sale, vendita allo
      specchio; uscita sull'incrocio opposto; stop -26,5%; ROI {0: 15%, 30 min: 10%, 60 min: 5%}.

Esecuzione come nel backtest di freqtrade: segnale alla chiusura della candela, operazione all'apertura della
successiva; stop e ROI controllati su massimo e minimo della candela (prima lo stop). Nessuna esecuzione 23:00-00:59
ora server. Costi: spread (minimo 0,20 $) + swap stimato (acquisti 3%/anno, vendite 1%/anno, notti di calendario),
pagati 0, 1 e 2 volte. Risultato: somma dei rendimenti % delle operazioni, senza leva.
Uso: python3 -I prova_freqtrade_futures.py <XAUUSD_M5.csv>
"""
import sys
import numpy as np
import pandas as pd

m5 = pd.read_csv(sys.argv[1])
m5['time'] = pd.to_datetime(m5['time'], format='%Y.%m.%d %H:%M')
m5 = m5[m5.time >= '2016-01-01'].set_index('time').sort_index()
m5['sp'] = m5.spread_points * 0.01


def bars(rule):
    if rule == '5min':
        b = m5.rename(columns={'tick_volume': 'volume'})[['open', 'high', 'low', 'close', 'volume', 'sp']]
    else:
        b = m5.resample(rule, label='left', closed='left').agg(
            dict(open='first', high='max', low='min', close='last', tick_volume='sum', sp='median')
        ).dropna(subset=['open']).rename(columns={'tick_volume': 'volume'})
    return b.reset_index()


def wilder(s, n):
    return s.ewm(alpha=1 / n, adjust=False).mean()


def atr_ta(d, n):                       # ATR di TA-Lib: media di Wilder del true range
    pc = d.close.shift(1)
    tr = pd.concat([d.high - d.low, (d.high - pc).abs(), (d.low - pc).abs()], axis=1).max(axis=1)
    return wilder(tr, n)


def adx_ta(d, n=14):                    # ADX di TA-Lib (Wilder)
    up, dn = d.high.diff(), -d.low.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    a = atr_ta(d, n)
    pdi = 100 * wilder(pd.Series(pdm, index=d.index), n) / a
    mdi = 100 * wilder(pd.Series(mdm, index=d.index), n) / a
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi)
    return wilder(dx, n)


def crossed_above(a, b):
    return (a > b) & (a.shift(1) <= b.shift(1))


def crossed_below(a, b):
    return (a < b) & (a.shift(1) >= b.shift(1))


def simulate(d, el, es, xl, xs, stop, roi, reverse=False):
    """el/es = segnali di entrata, xl/xs = segnali di uscita (alla chiusura della candela i)."""
    t = d.time.values
    o, h, l, c, sp = (d[k].values for k in ('open', 'high', 'low', 'close', 'sp'))
    hr = d.time.dt.hour.values
    roi_keys = sorted(roi)
    trades, pos, i = [], 0, 0
    entry = ent_i = None
    pending = 0          # segnale in attesa di esecuzione: +1/-1 entrata, 2 = uscita (e rigiro se reverse)

    def close(j, px):
        nonlocal pos
        ret = (px - entry) / entry * 100 * pos
        nights = (pd.Timestamp(t[j]).normalize() - pd.Timestamp(t[ent_i]).normalize()).days
        cost = max(sp[ent_i], 0.20) / entry * 100 + (3.0 if pos > 0 else 1.0) * nights / 365
        trades.append(dict(time=pd.Timestamp(t[ent_i]), dir=pos, ret=ret, cost=cost))
        pos = 0

    for j in range(1, len(d)):
        tradable = hr[j] not in (23, 0)
        # 1) esecuzione all'apertura dei segnali della candela precedente
        if tradable and pending:
            if pos != 0 and pending == 2:
                was = pos
                close(j, o[j])
                pending = -was if (reverse and ((was > 0 and es[j - 1]) or (was < 0 and el[j - 1]))) else 0
            if pos == 0 and pending in (1, -1):
                pos, entry, ent_i = pending, o[j], j
            pending = 0
        # 2) stop e ROI dentro la candela
        if pos != 0 and tradable:
            sl = entry * (1 - stop * pos)
            if (l[j] <= sl) if pos > 0 else (h[j] >= sl):
                close(j, o[j] if ((o[j] <= sl) if pos > 0 else (o[j] >= sl)) else sl)
            else:
                mins = (pd.Timestamp(t[j]) - pd.Timestamp(t[ent_i])).total_seconds() / 60
                r = roi[[k for k in roi_keys if k <= mins][-1]]
                tp = entry * (1 + r * pos)
                if (h[j] >= tp) if pos > 0 else (l[j] <= tp):
                    close(j, tp)
        # 3) segnali alla chiusura
        if pos == 0:
            if el[j]:
                pending = 1
            elif es[j]:
                pending = -1
        elif (pos > 0 and xl[j]) or (pos < 0 and xs[j]):
            pending = 2
    if pos != 0:
        close(len(d) - 1, c[-1])
    return pd.DataFrame(trades)


results = {}
# --- FAdxSmaStrategy ---
d = bars('1h')
adx = adx_ta(d, 14)
s12, s48 = d.close.rolling(12).mean(), d.close.rolling(48).mean()
el = ((adx > 30) & crossed_above(s12, s48)).values
es = ((adx > 30) & crossed_below(s12, s48)).values
x = (adx < 30).values
results['FAdxSmaStrategy (H1)'] = simulate(d, el, es, x, x, 0.05, {0: 0.05, 30: 0.10, 60: 0.075})
# --- VolatilitySystem ---
d = bars('3h')
atr2 = atr_ta(d, 14) * 2.0
chg = d.close.diff()
el = (chg > atr2.shift(1)).values
es = (-chg > atr2.shift(1)).values
results['VolatilitySystem (3 ore)'] = simulate(d, el, es, es, el, 1.0, {0: 100.0}, reverse=True)
# --- TrendFollowingStrategy ---
d = bars('5min')
obv = (np.sign(d.close.diff()).fillna(0) * d.volume).cumsum()
ema = d.close.ewm(span=20, adjust=False).mean()
el = ((d.close > ema) & (d.close.shift(1) <= ema.shift(1)) & (obv > obv.shift(1))).values
es = ((d.close < ema) & (d.close.shift(1) >= ema.shift(1)) & (obv < obv.shift(1))).values
xl = ((d.close < ema) & (d.close.shift(1) >= ema.shift(1)) & (obv > obv.shift(1))).values
xs = ((d.close > ema) & (d.close.shift(1) <= ema.shift(1)) & (obv < obv.shift(1))).values
results['TrendFollowingStrategy (M5)'] = simulate(d, el, es, xl, xs, 0.265, {0: 0.15, 30: 0.10, 60: 0.05})

for name, t in results.items():
    t['y'] = t.time.dt.year
    t.to_csv('freqtrade_' + name.split()[0] + '.csv', index=False)
    for cm in (0, 1, 2):
        net = t.ret - cm * t.cost
        L, S = net[t.dir > 0].sum(), net[t.dir < 0].sum()
        print(f"{name} costi x{cm}: operazioni={len(t)} (acquisti {int((t.dir > 0).sum())}, vendite {int((t.dir < 0).sum())}) "
              f"vinte={(net > 0).mean():.0%} totale={net.sum():+.1f}% acquisti={L:+.1f}% vendite={S:+.1f}% "
              f"2016-19={net[t.y <= 2019].sum():+.1f}% 2020-22={net[t.y >= 2020].sum():+.1f}%")
    print('   per anno (costi x2):', (t.ret - 2 * t.cost).groupby(t.y).sum().round(1).to_dict())
