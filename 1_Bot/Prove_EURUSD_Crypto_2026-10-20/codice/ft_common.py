"""Funzioni comuni per ricopiare in pandas le strategie freqtrade (indicatori alla TA-Lib e simulatore del
backtest di freqtrade: segnale alla chiusura della candela, operazione all'apertura della successiva, stop e
ROI controllati su massimo e minimo della candela, prima lo stop). Stesso simulatore usato sull'oro in
1_Bot/Prove_skill_esterne_2026-10-20/prova_freqtrade_futures.py, con costi e ore del mercato (mercati.py).
"""
import numpy as np
import pandas as pd
from mercati import swap_cost


def wilder(s, n):
    return s.ewm(alpha=1 / n, adjust=False).mean()


def atr_ta(d, n):
    pc = d.close.shift(1)
    tr = pd.concat([d.high - d.low, (d.high - pc).abs(), (d.low - pc).abs()], axis=1).max(axis=1)
    return wilder(tr, n)


def adx_ta(d, n=14):
    up, dn = d.high.diff(), -d.low.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    a = atr_ta(d, n)
    pdi = 100 * wilder(pd.Series(pdm, index=d.index), n) / a
    mdi = 100 * wilder(pd.Series(mdm, index=d.index), n) / a
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi)
    return wilder(dx, n)


def rsi_ta(close, n=14):
    delta = close.diff()
    gain = wilder(delta.clip(lower=0), n)
    loss = wilder((-delta).clip(lower=0), n)
    return 100 - 100 / (1 + gain / loss)


def crossed_above(a, b):
    return (a > b) & (a.shift(1) <= b.shift(1))


def crossed_below(a, b):
    return (a < b) & (a.shift(1) >= b.shift(1))


def simulate(d, cfg, el, es, xl, xs, stop, roi, reverse=False, trailing=None, start='2016-01-01'):
    """d: DataFrame con time, open, high, low, close, sp. el/es/xl/xs: array booleani (segnale alla chiusura).
    stop: perdita massima (frazione, es. 0.05). roi: {minuti: rendimento}. trailing: None oppure
    dict(positive=0.05, offset=0.10, only_offset=False) come in freqtrade. Ritorna le operazioni con
    ret (% lordo) e cost (% costo pagato una volta: costo per operazione + swap)."""
    t = d.time.values
    o, h, l, c, sp = (d[k].values for k in ('open', 'high', 'low', 'close', 'sp'))
    hr = d.time.dt.hour.values
    notrade = set(cfg['no_trade_hours'])
    roi_keys = sorted(roi)
    t_start = np.datetime64(pd.Timestamp(start))
    trades, pos = [], 0
    entry = ent_i = None
    peak = None
    pending = 0

    def close(j, px):
        nonlocal pos
        ret = (px - entry) / entry * 100 * pos
        nights = (pd.Timestamp(t[j]).normalize() - pd.Timestamp(t[ent_i]).normalize()).days
        cost = (sp[ent_i] + swap_cost(cfg, pos, entry, nights)) / entry * 100
        trades.append(dict(time=pd.Timestamp(t[ent_i]), dir=pos, ret=ret, cost=cost,
                           exit_time=pd.Timestamp(t[j])))
        pos = 0

    for j in range(1, len(d)):
        tradable = hr[j] not in notrade
        if tradable and pending:
            if pos != 0 and pending == 2:
                was = pos
                close(j, o[j])
                pending = -was if (reverse and ((was > 0 and es[j - 1]) or (was < 0 and el[j - 1]))) else 0
            if pos == 0 and pending in (1, -1) and t[j] >= t_start:
                pos, entry, ent_i = pending, o[j], j
                peak = entry
            pending = 0
        if pos != 0 and tradable:
            sl = entry * (1 - stop * pos)
            if trailing is not None:
                prof = (peak - entry) / entry * pos
                if (not trailing.get('only_offset')) or prof >= trailing['offset']:
                    dist = trailing['positive'] if prof >= trailing['offset'] else stop
                    tsl = peak * (1 - dist * pos)
                    sl = max(sl, tsl) if pos > 0 else min(sl, tsl)
            if (l[j] <= sl) if pos > 0 else (h[j] >= sl):
                close(j, o[j] if ((o[j] <= sl) if pos > 0 else (o[j] >= sl)) else sl)
            else:
                mins = (pd.Timestamp(t[j]) - pd.Timestamp(t[ent_i])).total_seconds() / 60
                r = roi[[k for k in roi_keys if k <= mins][-1]]
                tp = entry * (1 + r * pos)
                if (h[j] >= tp) if pos > 0 else (l[j] <= tp):
                    close(j, tp)
                elif trailing is not None:
                    peak = max(peak, h[j]) if pos > 0 else min(peak, l[j])
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


def report(name, t):
    """Righe di riepilogo per costi x0, x1, x2 (somma dei rendimenti % senza leva) e criteri Nucleus su x2."""
    lines = []
    if t.empty:
        return [f'{name}: nessuna operazione'], None
    t = t.copy()
    t['y'] = t.time.dt.year
    for cm in (0, 1, 2):
        net = t.ret - cm * t.cost
        L, S = net[t.dir > 0].sum(), net[t.dir < 0].sum()
        p1, p2 = net[t.y <= 2019].sum(), net[t.y >= 2020].sum()
        eq = (1 + net / 100).cumprod()
        dd = (1 - eq / eq.cummax()).max() * 100
        line = (f"{name} costi x{cm}: operazioni={len(t)} (acq {int((t.dir > 0).sum())}, ven {int((t.dir < 0).sum())}) "
                f"vinte={(net > 0).mean():.0%} totale={net.sum():+.1f}% acquisti={L:+.1f}% vendite={S:+.1f}% "
                f"2016-19={p1:+.1f}% 2020-22={p2:+.1f}% ultimo_terzo={net[t.time >= '2020-09-01'].sum():+.1f}% "
                f"drawdown={dd:.1f}%")
        if cm == 2:
            ok = [len(t) >= 100, net.sum() > 0, L > 0 and S > 0, p1 > 0 and p2 > 0, dd < 10]
            line += f" criteri={''.join('S' if x else 'N' for x in ok)} -> {'PASSA' if all(ok) else 'BOCCIATA'}"
        lines.append(line)
    lines.append('   per anno (costi x2): ' + str((t.ret - 2 * t.cost).groupby(t.y).sum().round(1).to_dict()))
    return lines, t
