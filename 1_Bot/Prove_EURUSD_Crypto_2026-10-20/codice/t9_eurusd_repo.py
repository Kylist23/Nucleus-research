"""Prova 9 - fase 2 su EUR/USD: sei strategie di altri repository, da sole e con il filtro (a) della skill
regime-detection. Regole registrate nel Manuale il 20/10/2026 alle 17:05 UTC, prima di qualsiasi calcolo; fonti,
commit e licenze in fonti_fase2.md; regole comuni del simulatore in fase2_motore.py.
Candele in ora server (New York + 7 ore); giorno = sessione che chiude alle 17:00 di New York (00:00 server).
  N1 inversione intraday (QuantConnect Lean): H1; sulle candele che finiscono tra le 10 e le 15 di New York compra
     se la chiusura e' sotto round(1,001 x media semplice 5, 6), altrimenti vende; agisce solo quando la
     direzione cambia rispetto all'ultima (anche del giorno prima); chiusura alla fine della candela delle 22 server.
  N2 Bollinger 20/2 + RSI 14 + regime giornaliero (OptiFabian, configurazione "D k=2.0 rsi=30/70"): M15; entra
     alla banda con RSI <= 30 (acquisto) o >= 70 (vendita) solo se il regime giornaliero dell'ultimo giorno chiuso
     e' diverso da zero (la chiusura giornaliera ha toccato una banda e non e' ancora tornata alla media); esce
     alla media; senza stop.
  N3 HLHB (BabyPips, regole da estratti non verificati): H1; medie esponenziali 5/10 e RSI 10 sul prezzo mediano
     che incrociano nella stessa candela, ADX 14 sopra 25; trailing di 150 pip, target 400 pip, il segnale opposto
     gira la posizione, chiusura il venerdi' alla fine della candela delle 22 server.
  N4 rottura di Londra (tradlysis): range 00-08 Londra valido tra 1,5 e 6 ATR orari; prima chiusura M15 oltre il
     range di 0,1 ATR M15 tra le 08 e le 12 di Londra; stop a meta' range (almeno 5 pip), niente se lo stop supera
     40 pip; target 2R; uscita forzata alla chiusura della candela delle 22:45 server (aggiunta registrata).
  N5 RSI2 di Connors (jesse): candele da 3 ore; compra sopra la media 200 con RSI 2 <= 10, vende sotto con RSI 2
     >= 90; esce quando il prezzo torna oltre la media 5.
  N6 Dynamic Breakout II (QuantConnect Tutorials): finestra di N giorni (parte da 20, cambia ogni giorno con la
     volatilita' delle ultime 30 chiusure, tra 20 e 60); compra se la chiusura di ieri e' sopra la banda di
     Bollinger (media esponenziale N, 2 deviazioni) e oggi il prezzo supera il massimo degli ultimi N giorni;
     vende allo specchio; esce quando il prezzo passa la media semplice delle ultime N chiusure. Controllo
     durante il giorno sulle candele M15.
Filtro (a): N3, N4, N6 (tendenza) solo se l'ADX 14 giornaliero del giorno prima e' sopra 22; N1, N2, N5 (ritorno
alla media) solo se e' sotto o uguale a 22 e il percentile dell'ATR giornaliero su 80 giorni non supera 0,65.
Uso: python3 t9_eurusd_repo.py <percorso regime_backtest.py>
"""
import importlib.util
import sys
import numpy as np
import pandas as pd
from mercati import load_fase2, resample
from ft_common import report
from fase2_motore import (ema, sma, bollinger, rsi_ta, atr_ta, adx_ta, crossed_above, crossed_below,
                          filtro_regime, permessi_regime, giorno_prima, run_target, run_signals, comprare_e_tenere)

spec = importlib.util.spec_from_file_location('regime_backtest', sys.argv[1])
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)

base, cfg = load_fase2('EURUSD')
PIP = 0.0001
H1 = resample(base, '1h')
H3 = resample(base, '3h')
D1 = resample(base, '1D')
D1 = D1[D1.index.dayofweek < 5]
FR = filtro_regime(D1, rb)


def ok_regime(b, tipo, usa):
    return permessi_regime(FR, b.index, tipo) if usa else None


def london(idx):
    ny = pd.DatetimeIndex(idx) - pd.Timedelta(hours=7)
    return ny.tz_localize('America/New_York', ambiguous='NaT', nonexistent='NaT') \
             .tz_convert('Europe/London').tz_localize(None)


# ---------------------------------------------------------------- N1
def n1(usa_filtro):
    b = H1
    ok = ok_regime(b, 'media', usa_filtro)
    hrs = b.index.hour
    dec = (hrs >= 16) & (hrs <= 21)          # candele che finiscono tra le 10:00 e le 15:00 di New York
    cl, s5 = b.close.to_numpy(), sma(b.close, 5).to_numpy()
    target = np.zeros(len(b), int)
    prev, active = 0, 0
    for t in range(len(b)):
        if not dec[t]:
            active = 0                       # fuori dalle ore delle decisioni la posizione voluta e' zero
        if dec[t] and not np.isnan(s5[t]):
            d = 1 if cl[t] < round(s5[t] * 1.001, 6) else -1
            if d != prev:
                prev = d
                active = d if (ok is None or ok[t]) else 0
        target[t] = active
    return run_target(b, cfg, target, flat_close=(hrs == 22))


# ---------------------------------------------------------------- N2
def regime_giornaliero():
    up, mid, lo = bollinger(D1.close, 20, 2.0, ddof=1)
    p, u, m, lw = (x.to_numpy(float) for x in (D1.close, up, mid, lo))
    st, out = 0, np.zeros(len(D1))
    for t in range(len(D1)):
        if np.isnan(u[t]) or np.isnan(m[t]) or np.isnan(lw[t]):
            st = 0
        elif st == 0:
            st = 1 if p[t] <= lw[t] else (-1 if p[t] >= u[t] else 0)
        elif st == 1 and p[t] >= m[t]:
            st = 0
        elif st == -1 and p[t] <= m[t]:
            st = 0
        out[t] = st
    return pd.DataFrame({'r': out}, index=D1.index)


def n2(usa_filtro):
    b = base
    ok = ok_regime(b, 'media', usa_filtro)
    up, mid, lo = bollinger(b.close, 20, 2.0, ddof=1)
    rsi = rsi_ta(b.close, 14)
    reg = giorno_prima(regime_giornaliero(), b.index).r.to_numpy()
    p, u, m, lw, r = (np.asarray(x, float) for x in (b.close, up, mid, lo, rsi))
    sig = np.zeros(len(b), int)
    state, pend = 0, 0
    for t in range(len(b)):
        if np.isnan(u[t]) or np.isnan(m[t]) or np.isnan(lw[t]) or np.isnan(r[t]) or np.isnan(reg[t]):
            state, pend = 0, 0
            continue
        if state == 0:
            side = 0
            if lw[t] < p[t] < u[t]:
                pend = 0
            elif p[t] <= lw[t] and pend != 1:
                side = 1
            elif p[t] >= u[t] and pend != -1:
                side = -1
            if side:
                rsi_ok = r[t] <= 30 if side == 1 else r[t] >= 70
                if rsi_ok:                                     # altrimenti 'wait': si riprova alla candela dopo
                    if reg[t] == 0 or (ok is not None and not ok[t]):
                        pend = side                            # 'skip': salta tutto il tocco di banda
                    else:
                        state = side
        elif (state == 1 and p[t] >= m[t]) or (state == -1 and p[t] <= m[t]):
            state, pend = 0, 0
        sig[t] = state
    return run_target(b, cfg, sig)


# ---------------------------------------------------------------- N3
def n3(usa_filtro):
    b = H1
    ok = ok_regime(b, 'tendenza', usa_filtro)
    e5, e10 = ema(b.close, 5), ema(b.close, 10)
    r10 = rsi_ta((b.high + b.low) / 2, 10)
    adx = adx_ta(b, 14)
    fifty = pd.Series(50.0, index=b.index)
    el = crossed_above(e5, e10) & crossed_above(r10, fifty) & (adx > 25)
    es = crossed_below(e5, e10) & crossed_below(r10, fifty) & (adx > 25)
    fri = b.index.dayofweek == 4
    z = np.zeros(len(b), bool)
    return run_signals(b, cfg, el, es, z, z, ok_l=ok, ok_s=ok, reverse=True, trail_dist=150 * PIP,
                       tgt_dist=400 * PIP, flat_close=fri & (b.index.hour == 22), no_entry=fri & (b.index.hour >= 22))


# ---------------------------------------------------------------- N4
def n4(usa_filtro):
    b = base
    ok = ok_regime(b, 'tendenza', usa_filtro)
    n = len(b)
    lon, lon_h1 = london(b.index), london(H1.index)
    atr_h1, atr_m15 = atr_ta(H1, 14), atr_ta(b, 14).to_numpy()
    last_h1 = (b.index + pd.Timedelta(minutes=15)).floor('h') - pd.Timedelta(hours=1)
    atr_h1_at = atr_h1.reindex(last_h1).to_numpy()
    r = pd.DataFrame({'d': lon_h1.normalize(), 'hr': lon_h1.hour, 'hi': H1.high.to_numpy(), 'lo': H1.low.to_numpy()})
    rng = r[r.hr <= 7].groupby('d').agg(hi=('hi', 'max'), lo=('lo', 'min'), k=('hi', 'size'))
    rng = rng[rng.k >= 7]
    lmin = lon.hour * 60 + lon.minute
    win = (lmin >= 8 * 60) & (lmin <= 11 * 60 + 45) & (lon.dayofweek < 5)
    c = b.close.to_numpy()
    el, es = np.zeros(n, bool), np.zeros(n, bool)
    stop_px, tgt_px = np.full(n, np.nan), np.full(n, np.nan)
    pos_win = np.flatnonzero(win)
    days = lon.normalize()[pos_win]
    for day, ks in pd.Series(pos_win).groupby(days.to_numpy()):
        if day not in rng.index:
            continue
        hi, lo = rng.at[day, 'hi'], rng.at[day, 'lo']
        height = hi - lo
        above = below = False
        for k in ks.to_numpy():
            ah, am = atr_h1_at[k], atr_m15[k]
            if not (np.isnan(ah) or np.isnan(am) or ah <= 0 or am <= 0):
                width_ok = 1.5 <= height / ah <= 6.0
                buf = 0.1 * am
                side = 1 if c[k] > hi + buf else (-1 if c[k] < lo - buf else 0)
                fresh = (side == 1 and not above) or (side == -1 and not below)
                if side and fresh and width_ok:
                    edge = hi if side == 1 else lo
                    stop = edge - side * height * 0.5
                    if (c[k] - stop) * side < 5 * PIP:
                        stop = c[k] - side * 5 * PIP
                    risk = abs(c[k] - stop)
                    if round(risk / PIP, 1) <= 40:
                        (el if side == 1 else es)[k] = True
                        stop_px[k], tgt_px[k] = stop, c[k] + side * 2 * risk
            above = above or c[k] > hi
            below = below or c[k] < lo
    z = np.zeros(n, bool)
    fc = (b.index.hour == 22) & (b.index.minute == 45)
    return run_signals(b, cfg, el, es, z, z, ok_l=ok, ok_s=ok, stop_px=stop_px, tgt_px=tgt_px, flat_close=fc)


# ---------------------------------------------------------------- N5
def n5(usa_filtro, b=None, tag='media'):
    b = H3 if b is None else b
    ok = ok_regime(b, tag, usa_filtro)
    s5, s200, r2 = sma(b.close, 5), sma(b.close, 200), rsi_ta(b.close, 2)
    el = (b.close > s200) & (r2 <= 10)
    es = (b.close < s200) & (r2 >= 90)
    return run_signals(b, cfg, el, es, b.close > s5, b.close < s5, ok_l=ok, ok_s=ok, same_bar=True)


# ---------------------------------------------------------------- N6
def livelli_dbo():
    d = D1
    vol = d.close.rolling(30).std(ddof=0).to_numpy()
    N = np.full(len(d), np.nan)
    cur = 20
    for t in range(1, len(d)):
        if np.isnan(vol[t]) or np.isnan(vol[t - 1]) or vol[t] == 0:
            continue
        cur = int(min(60, max(20, round(cur * (1 + (vol[t] - vol[t - 1]) / vol[t])))))
        N[t] = cur
    cols = dict(up=np.full(len(d), np.nan), lo=np.full(len(d), np.nan), buy=np.full(len(d), np.nan),
                sell=np.full(len(d), np.nan), liq=np.full(len(d), np.nan))
    for k in range(20, 61):
        sel = N == k
        if not sel.any():
            continue
        e, sd = ema(d.close, k).to_numpy(), d.close.rolling(k).std(ddof=0).to_numpy()
        cols['up'][sel], cols['lo'][sel] = (e + 2 * sd)[sel], (e - 2 * sd)[sel]
        cols['buy'][sel] = d.high.rolling(k).max().to_numpy()[sel]
        cols['sell'][sel] = d.low.rolling(k).min().to_numpy()[sel]
        cols['liq'][sel] = d.close.rolling(k).mean().to_numpy()[sel]
    lv = pd.DataFrame(cols, index=d.index)
    lv['setup_l'] = (d.close > lv.up).astype(float)
    lv['setup_s'] = (d.close < lv.lo).astype(float)
    lv['N'] = N
    return lv


def n6(usa_filtro):
    b = base
    ok = ok_regime(b, 'tendenza', usa_filtro)
    g = giorno_prima(livelli_dbo(), b.index)
    el = (g.setup_l == 1) & (b.high > g.buy)
    es = (g.setup_s == 1) & (b.low < g.sell)
    xl, xs = b.low < g.liq, b.high > g.liq
    return run_signals(b, cfg, el, es, xl, xs, ok_l=ok, ok_s=ok)


STRATEGIE = [('N1 inversione intraday (Lean, H1)', n1), ('N2 Bollinger+RSI+regime (OptiFabian, M15)', n2),
             ('N3 HLHB (BabyPips, H1)', n3), ('N4 rottura di Londra (tradlysis, M15)', n4),
             ('N5 RSI2 Connors (jesse, 3 ore)', n5), ('N6 Dynamic Breakout II (QuantConnect, giornaliero)', n6)]

if __name__ == '__main__':
    out = [f"{cfg['nome']} - fase 2, somma dei rendimenti % delle operazioni senza leva, dal 2016-01-01 al "
           f"{cfg['fine']}; comprare e tenere = {comprare_e_tenere(base):+.1f}%"]
    for name, fn in STRATEGIE:
        code = name.split()[0]
        for usa in (False, True):
            label = name + (' + filtro regime-detection' if usa else '')
            t = fn(usa)
            lines, tt = report(label, t)
            out += lines
            if tt is not None:
                out.append('   uscite: ' + str(t.motivo.value_counts().to_dict()) +
                           f"; durata media {(t.exit_time - t.time).mean()}")
                t.to_csv(f"../EURUSD/t9_{code}{'_filtro' if usa else ''}.csv", index=False)
        out.append('')
    txt = '\n'.join(out)
    print(txt)
    open('../EURUSD/t9_fase2_risultati.txt', 'w').write(txt + '\n')
