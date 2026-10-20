"""Prova 10 - fase 2 su Bitcoin: nove strategie di altri repository, da sole, con il filtro (a) della skill
regime-detection e con il filtro (b) di tendenza di crypto-regime-analyzer. Regole registrate nel Manuale il
20/10/2026 alle 17:05 UTC, prima di qualsiasi calcolo; fonti in fonti_fase2.md; simulatore in fase2_motore.py.
Candele in ora UTC (giorno UTC, candele da 3 e 6 ore allineate a UTC).
  K1 Donchian 20 con media 200 (jesse): 6 ore, solo acquisti; compra se la chiusura supera il massimo delle 20
     candele precedenti ed e' sopra la media 200; esce quando chiude sotto il minimo delle 20 candele precedenti.
  K2 rottura di volatilita' di Larry Williams, k = 0,5 (pyupbit-autotrade): giorno UTC, solo acquisti; compra
     quando il prezzo supera apertura + 0,5 x (massimo - minimo di ieri), esce alla chiusura del giorno. Il
     superamento si controlla sulle candele da 5 minuti e si compra all'apertura della candela successiva.
  K2b la stessa con il filtro della media a 15 giorni dello script: compra solo quando il prezzo supera anche la
     media delle 14 chiusure precedenti (la media a 15 dello script contiene il prezzo del momento).
  K3 RSI2 di Connors (jesse): 3 ore, acquisti e vendite (come N5).
  K4 BbandRsi (freqtrade): H1, solo acquisti; RSI 14 sotto 30 e chiusura sotto la banda bassa di Bollinger 20/2
     sul prezzo tipico; esce con RSI sopra 70, target 10%, stop 25%.
  K5 SimpleBollinger (jesse): H1, solo acquisti; chiusura sopra la banda alta (20/2 sul prezzo medio) e sopra la
     nuvola Ichimoku; esce quando chiude sotto la media.
  K6 TradingView_RSI (jesse): H1, solo acquisti; RSI 5 che risale sopra 35; stop 5%, target 10%; esce se l'RSI
     scende sotto 75 o sotto 10.
  K7 Supertrend (freqtrade): H1, solo acquisti; tre supertrend 'up' per entrare, tre 'down' per uscire; ROI
     {0: 8,7%, 372 min: 5,8%, 861: 2,9%, 2221: 0}, stop 26,5% con il trailing del file.
  K8 incrocio delle medie 50/200 (jesse): 3 ore, sempre a mercato, acquisti e vendite.
Filtro (a): K1, K2, K2b, K5, K7, K8 (tendenza) solo se l'ADX 14 giornaliero del giorno prima e' sopra 22; K3, K4,
K6 (ritorno alla media) solo se e' sotto o uguale a 22 e il percentile dell'ATR giornaliero su 80 giorni non
supera 0,65. Filtro (b): acquisti solo con punteggio di tendenza del giorno prima almeno 55, vendite solo con
punteggio al massimo 45.
Uso: python3 t10_btc_repo.py <percorso regime_backtest.py>
"""
import importlib.util
import sys
import numpy as np
import pandas as pd
from mercati import load_fase2, resample, swap_cost
from ft_common import report
from fase2_motore import (sma, bollinger, ichimoku_spans, supertrend_dir, rsi_ta, filtro_regime, permessi_regime,
                          punteggio_tendenza_btc, giorno_prima, run_signals, comprare_e_tenere)

spec = importlib.util.spec_from_file_location('regime_backtest', sys.argv[1])
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)

base, cfg = load_fase2('BTC')
H1, H3, H6, D1 = (resample(base, r) for r in ('1h', '3h', '6h', '1D'))
FR = filtro_regime(D1, rb)
SCORE = pd.DataFrame({'s': punteggio_tendenza_btc(D1.close)}, index=D1.index)
TIPO = dict(K1='tendenza', K2='tendenza', K2b='tendenza', K3='media', K4='media', K5='tendenza', K6='media',
            K7='tendenza', K8='tendenza')


def permessi(b, code, filtro):
    """(ok_acquisti, ok_vendite) per le candele di b."""
    if filtro == 'a':
        ok = permessi_regime(FR, b.index, TIPO[code])
        return ok, ok
    if filtro == 'b':
        s = giorno_prima(SCORE, b.index).s
        return (s >= 55).to_numpy(bool), (s <= 45).to_numpy(bool)
    return None, None


def z(b):
    return np.zeros(len(b), bool)


def k1(f):
    b = H6
    ok_l, _ = permessi(b, 'K1', f)
    up, dn = b.high.rolling(20).max().shift(1), b.low.rolling(20).min().shift(1)
    el = (b.close > up) & (b.close > sma(b.close, 200))
    return run_signals(b, cfg, el, z(b), b.close < dn, z(b), ok_l=ok_l, same_bar=True)


def k2(f, code='K2'):
    d = D1
    level = d.open + 0.5 * (d.high - d.low).shift(1)
    if code == 'K2b':
        level = np.maximum(level, d.close.rolling(14).mean().shift(1))
    ok_l, _ = permessi(d, code, f)
    ok_day = pd.Series(np.ones(len(d), bool) if ok_l is None else ok_l, index=d.index)
    m = base[base.index >= '2016-01-01']
    day = m.index.normalize()
    lv = level.reindex(day).to_numpy()
    hit = (m.high.to_numpy() > lv) & ok_day.reindex(day).fillna(False).to_numpy(bool)
    pos = np.arange(len(m))
    frame = pd.DataFrame({'day': day, 'hit': hit, 'pos': pos})
    first = frame[frame.hit].groupby('day').pos.min()
    last = frame.groupby('day').pos.max()
    o, c, sp = m.open.to_numpy(), m.close.to_numpy(), m.sp.to_numpy()
    rows = []
    for dd, i in first.items():
        j, k = i + 1, last[dd]
        if j > k:                     # superamento nell'ultima candela del giorno: niente operazione
            continue
        entry, ex = o[j], c[k]
        cost = (sp[j] + swap_cost(cfg, 1, entry, 0)) / entry * 100
        rows.append(dict(time=m.index[j], dir=1, entry=entry, exit_time=m.index[k], exit=ex,
                         ret=(ex - entry) / entry * 100, cost=cost, motivo='fine giorno'))
    return pd.DataFrame(rows, columns=['time', 'dir', 'entry', 'exit_time', 'exit', 'ret', 'cost', 'motivo'])


def k2b(f):
    return k2(f, 'K2b')


def k3(f):
    b = H3
    ok_l, ok_s = permessi(b, 'K3', f)
    s5, s200, r2 = sma(b.close, 5), sma(b.close, 200), rsi_ta(b.close, 2)
    el = (b.close > s200) & (r2 <= 10)
    es = (b.close < s200) & (r2 >= 90)
    return run_signals(b, cfg, el, es, b.close > s5, b.close < s5, ok_l=ok_l, ok_s=ok_s, same_bar=True)


def k4(f):
    b = H1
    ok_l, _ = permessi(b, 'K4', f)
    up, mid, lo = bollinger((b.high + b.low + b.close) / 3, 20, 2.0, ddof=1)
    rsi = rsi_ta(b.close, 14)
    return run_signals(b, cfg, (rsi < 30) & (b.close < lo), z(b), rsi > 70, z(b), ok_l=ok_l, stop_frac=0.25,
                       roi={0: 0.10}, ignore_exit_if_entry=True)


def k5(f):
    b = H1
    ok_l, _ = permessi(b, 'K5', f)
    up, mid, lo = bollinger((b.high + b.low) / 2, 20, 2.0, ddof=0)
    sa, sb = ichimoku_spans(b)
    el = (b.close > up) & (b.close > sa) & (b.close > sb)
    return run_signals(b, cfg, el, z(b), b.close < mid, z(b), ok_l=ok_l, same_bar=True)


def k6(f):
    b = H1
    ok_l, _ = permessi(b, 'K6', f)
    r5 = rsi_ta(b.close, 5)
    p = r5.shift(1)
    el = (r5 > 35) & (p <= 35)
    xl = ((r5 < 75) & (p >= 75)) | ((r5 < 10) & (p >= 10))
    return run_signals(b, cfg, el, z(b), xl, z(b), ok_l=ok_l, stop_frac=0.05, tgt_frac=0.10, same_bar=True)


def k7(f):
    b = H1
    ok_l, _ = permessi(b, 'K7', f)
    vol = (b.volume > 0).to_numpy()
    up = np.all([supertrend_dir(b, m, p) == 1 for m, p in ((4, 8), (7, 9), (1, 8))], axis=0) & vol
    dn = np.all([supertrend_dir(b, m, p) == -1 for m, p in ((1, 16), (3, 18), (6, 18))], axis=0) & vol
    return run_signals(b, cfg, up, z(b), dn, z(b), ok_l=ok_l, stop_frac=0.265,
                       roi={0: 0.087, 372: 0.058, 861: 0.029, 2221: 0.0},
                       ft_trailing=dict(positive=0.05, offset=0.144, only_offset=False), ignore_exit_if_entry=True)


def k8(f):
    b = H3
    ok_l, ok_s = permessi(b, 'K8', f)
    fa, sl = sma(b.close, 50), sma(b.close, 200)
    return run_signals(b, cfg, fa > sl, fa < sl, fa < sl, fa > sl, ok_l=ok_l, ok_s=ok_s, same_bar=True)


STRATEGIE = [('K1 Donchian 20 + media 200 (jesse, 6 ore)', k1), ('K2 rottura di volatilita k=0,5 (giornaliero)', k2),
             ('K2b rottura di volatilita + media 15', k2b), ('K3 RSI2 Connors (jesse, 3 ore)', k3),
             ('K4 BbandRsi (freqtrade, H1)', k4), ('K5 SimpleBollinger (jesse, H1)', k5),
             ('K6 TradingView_RSI (jesse, H1)', k6), ('K7 Supertrend (freqtrade, H1)', k7),
             ('K8 medie 50/200 (jesse, 3 ore)', k8)]
FILTRI = [(None, ''), ('a', ' + filtro regime-detection'), ('b', ' + filtro tendenza crypto-regime')]

if __name__ == '__main__':
    out = [f"{cfg['nome']} - fase 2, somma dei rendimenti % delle operazioni senza leva, dal 2016-01-01 al "
           f"{cfg['fine']}; comprare e tenere = {comprare_e_tenere(base):+.1f}%",
           "Nota: per le strategie solo acquisti il criterio 'acquisti e vendite entrambi positivi' non puo' "
           "essere soddisfatto (vendite = 0)."]
    for name, fn in STRATEGIE:
        code = name.split()[0]
        for f, suff in FILTRI:
            t = fn(f)
            lines, tt = report(name + suff, t)
            out += lines
            if tt is not None:
                net = t.ret - 2 * t.cost
                eq = (1 + net / 100).cumprod()
                out.append('   uscite: ' + str(t.motivo.value_counts().to_dict()) +
                           f"; durata media {(t.exit_time - t.time).mean()}; capitale composto costi x2 "
                           f"{(eq.iloc[-1] - 1) * 100:+.1f}%")
                t.to_csv(f"../BTC/t10_{code}{'_filtro_' + f if f else ''}.csv", index=False)
        out.append('')
    txt = '\n'.join(out)
    print(txt)
    open('../BTC/t10_fase2_risultati.txt', 'w').write(txt + '\n')
