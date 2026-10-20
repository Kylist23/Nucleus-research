"""Fase 2 della campagna EUR/USD e Bitcoin: indicatori, filtri e simulatore comuni alle strategie prese da altri
repository (regole riscritte in pandas, fonti in fonti_fase2.md).

Regole comuni registrate nel Manuale il 20/10/2026 alle 17:05 UTC, prima di qualsiasi calcolo:
- ogni segnale nasce alla chiusura di una candela e si esegue all'apertura della candela successiva in cui il
  broker esegue (su EUR/USD niente esecuzioni dalle 23:00 alle 00:59 server), anche dove jesse eseguirebbe alla
  chiusura;
- stop e target si controllano su massimi e minimi della candela, prima lo stop; se la candela apre gia' oltre lo
  stop si esce all'apertura;
- costo per operazione e swap come nella fase 1 (mercati.py), pagati due volte nei criteri;
- risultati in % del capitale senza leva: ogni operazione usa tutto il capitale.
"""
import numpy as np
import pandas as pd
from mercati import swap_cost
from ft_common import atr_ta, adx_ta, rsi_ta, crossed_above, crossed_below  # noqa: F401 (riusati dalle prove)


# ---------------------------------------------------------------- indicatori

def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def sma(s, n):
    return s.rolling(n).mean()


def bollinger(src, n=20, k=2.0, ddof=1):
    """ddof=1: deviazione standard campionaria (qtpylib, OptiFabian); ddof=0: della popolazione (jesse)."""
    m = src.rolling(n).mean()
    sd = src.rolling(n).std(ddof=ddof)
    return m + k * sd, m, m - k * sd


def ichimoku_spans(d, conv=9, base=26, lag=52, disp=26):
    """span_a e span_b come jesse-rust: calcolati sulle candele fino a disp-1 candele prima, senza futuro."""
    def mid(n):
        return (d.high.rolling(n).max() + d.low.rolling(n).min()) / 2
    return ((mid(conv) + mid(base)) / 2).shift(disp - 1), mid(lag).shift(disp - 1)


def supertrend_dir(d, m, p):
    """Supertrend di freqtrade/technical (commit ce0e895): ATR = media semplice del true range di TA-Lib.
    Ritorna +1 ('up'), -1 ('down') oppure 0 (non ancora definito)."""
    h, l, c = (d[k].to_numpy(float) for k in ('high', 'low', 'close'))
    pc = np.concatenate([[np.nan], c[:-1]])
    tr = np.fmax(h - l, np.fmax(np.abs(h - pc), np.abs(l - pc)))
    tr[0] = np.nan                                   # TRANGE di TA-Lib non ha la prima candela
    atr = pd.Series(tr).rolling(p).mean().to_numpy()
    bub, blb = (h + l) / 2 + m * atr, (h + l) / 2 - m * atr
    n = len(c)
    fub, flb, st = np.zeros(n), np.zeros(n), np.zeros(n)
    for i in range(p, n):
        fub[i] = bub[i] if (bub[i] < fub[i - 1] or c[i - 1] > fub[i - 1]) else fub[i - 1]
        flb[i] = blb[i] if (blb[i] > flb[i - 1] or c[i - 1] < flb[i - 1]) else flb[i - 1]
    for i in range(p, n):
        if st[i - 1] == fub[i - 1]:
            st[i] = fub[i] if c[i] <= fub[i] else flb[i]
        elif st[i - 1] == flb[i - 1]:
            st[i] = flb[i] if c[i] >= flb[i] else fub[i]
    return np.where(st > 0, np.where(c < st, -1, 1), 0)


# ---------------------------------------------------------------- filtri "insieme"

def filtro_regime(daily, rb):
    """Filtro (a): ADX(14) e percentile dell'ATR(14) su 80 giorni calcolati con le funzioni della skill
    regime-detection (rb = modulo regime_backtest.py) sulle candele giornaliere."""
    adx = rb.compute_adx(daily['high'], daily['low'], daily['close'], rb.ADX_PERIOD)
    vp = rb.compute_atr_percentile(daily['high'], daily['low'], daily['close'], rb.ATR_PERIOD, rb.VOL_LOOKBACK)
    return pd.DataFrame({'adx': adx, 'vp': vp}, index=daily.index)


def punteggio_tendenza_btc(close):
    """Filtro (b): punteggio di tendenza del Bitcoin di crypto-regime-analyzer (btc_trend_calculator.py, commit
    cb0f3aa), riscritto: base dalla posizione di prezzo, media 50 e media 200; +10/-10 se la media 200 sale o
    scende rispetto a 20 giorni prima; 50 (nessun dato) con meno di 220 chiusure."""
    s50, s200 = close.rolling(50).mean(), close.rolling(200).mean()
    s200p = close.rolling(200).mean().shift(20)
    p = close
    base = np.select(
        [(p > s50) & (s50 > s200),
         (p > s200) & (p <= s50) & (s50 > s200),
         (p <= s200) & (p <= s50) & (s50 > s200),
         (p > s50) & (s50 <= s200)],
        [90, 65, 55, 45], default=15).astype(float)
    slope = np.where(s200 > s200p, 10, np.where(s200 < s200p, -10, 0))
    score = np.clip(base + slope, 0, 100)
    enough = np.arange(len(close)) + 1 >= 220
    return pd.Series(np.where(enough & s200p.notna().to_numpy(), score, 50.0), index=close.index)


def giorno_prima(f, idx):
    """Per ogni candela di idx, i valori dell'ultimo giorno CHIUSO prima della data della candela."""
    days = f.index.normalize().to_numpy()
    pos = np.searchsorted(days, pd.DatetimeIndex(idx).normalize().to_numpy(), side='left') - 1
    out = f.iloc[np.clip(pos, 0, None)].copy()
    out[pos < 0] = np.nan
    out.index = idx
    return out


def permessi_regime(fr, idx, tipo):
    """tipo 'tendenza': ADX del giorno prima sopra 22; 'media': ADX sotto o uguale a 22 e percentile dell'ATR
    non sopra 0,65 (soglie di detect_regime della skill). Valori mancanti = entrata non permessa."""
    g = giorno_prima(fr, idx)
    if tipo == 'tendenza':
        ok = g.adx > 22
    else:
        ok = (g.adx <= 22) & (g.vp <= 0.65)
    return ok.fillna(False).to_numpy(bool)


# ---------------------------------------------------------------- simulatori

class Registro:
    """Raccoglie le operazioni: rendimento % lordo e costo % pagato una volta (costo per operazione + swap)."""

    def __init__(self, b, cfg):
        self.t = b.index
        self.sp = b['sp'].to_numpy(float)
        self.cfg = cfg
        self.rows = []

    def chiudi(self, ent_i, d, entry, j, px, motivo):
        nights = (self.t[j].normalize() - self.t[ent_i].normalize()).days
        cost = (self.sp[ent_i] + swap_cost(self.cfg, d, entry, nights)) / entry * 100
        self.rows.append(dict(time=self.t[ent_i], dir=d, entry=entry, exit_time=self.t[j], exit=px,
                              ret=(px - entry) / entry * 100 * d, cost=cost, motivo=motivo))

    def df(self):
        cols = ['time', 'dir', 'entry', 'exit_time', 'exit', 'ret', 'cost', 'motivo']
        return pd.DataFrame(self.rows, columns=cols)


def _tradable(b, cfg):
    return ~np.isin(b.index.hour, list(cfg['no_trade_hours']))


def run_target(b, cfg, target, flat_close=None, start='2016-01-01'):
    """Posizione voluta target[t] (-1, 0, +1) decisa alla chiusura della candela t ed eseguita all'apertura della
    prima candela successiva in cui il broker esegue. flat_close[t]: chiusura forzata alla chiusura di t."""
    o, c = b['open'].to_numpy(float), b['close'].to_numpy(float)
    trad = _tradable(b, cfg)
    t0 = np.searchsorted(b.index.to_numpy(), np.datetime64(pd.Timestamp(start)))
    fc = np.zeros(len(b), bool) if flat_close is None else np.asarray(flat_close, bool)
    reg = Registro(b, cfg)
    pos, entry, ent_i = 0, None, None
    for j in range(1, len(b)):
        if trad[j]:
            want = int(target[j - 1])
            if want != pos:
                if pos != 0:
                    reg.chiudi(ent_i, pos, entry, j, o[j], 'segnale')
                    pos = 0
                if want != 0 and j >= t0:
                    pos, entry, ent_i = want, o[j], j
        if pos != 0 and fc[j]:
            reg.chiudi(ent_i, pos, entry, j, c[j], 'orario')
            pos = 0
    if pos != 0:
        reg.chiudi(ent_i, pos, entry, len(b) - 1, c[-1], 'fine dati')
    return reg.df()


def run_signals(b, cfg, el, es, xl, xs, *, ok_l=None, ok_s=None, reverse=False, same_bar=False,
                ignore_exit_if_entry=False, stop_frac=None, tgt_frac=None, stop_px=None, tgt_px=None,
                stop_dist=None, tgt_dist=None, trail_dist=None, roi=None, ft_trailing=None, flat_close=None, no_entry=None,
                start='2016-01-01'):
    """Simulatore a segnali. el/es: entrata acquisto/vendita; xl/xs: uscita acquisto/vendita (alla chiusura).
    ok_l/ok_s: entrate permesse dai filtri. reverse: il segnale opposto chiude e gira la posizione.
    same_bar: dopo un'uscita si guardano le entrate sulla stessa candela (jesse). ignore_exit_if_entry: uscita
    ignorata se c'e' anche il segnale di entrata (freqtrade). stop_frac/tgt_frac: stop e target in frazione del
    prezzo di entrata; stop_px/tgt_px: livelli fissati alla candela del segnale; stop_dist/tgt_dist: distanze
    dal prezzo di entrata in unita' di prezzo (per esempio pip); trail_dist: trailing in unita'
    di prezzo dal massimo (o minimo) raggiunto; roi: tabella freqtrade {minuti: rendimento}; ft_trailing:
    trailing di freqtrade dict(positive, offset, only_offset). flat_close: chiusura forzata alla chiusura della
    candela; no_entry: candele i cui segnali di entrata non si usano."""
    n = len(b)
    tt = b.index
    o, h, l, c = (b[k].to_numpy(float) for k in ('open', 'high', 'low', 'close'))
    trad = _tradable(b, cfg)
    t0 = np.searchsorted(tt.to_numpy(), np.datetime64(pd.Timestamp(start)))
    one = np.ones(n, bool)
    ok_l = one if ok_l is None else np.asarray(ok_l, bool)
    ok_s = one if ok_s is None else np.asarray(ok_s, bool)
    fc = np.zeros(n, bool) if flat_close is None else np.asarray(flat_close, bool)
    ne = np.zeros(n, bool) if no_entry is None else np.asarray(no_entry, bool)
    el, es, xl, xs = (np.nan_to_num(np.asarray(x, float)).astype(bool) for x in (el, es, xl, xs))
    roi_keys = sorted(roi) if roi else []
    reg = Registro(b, cfg)
    pos, entry, ent_i, peak, sl, tp = 0, None, None, None, None, None
    p_exit, p_entry, p_sig = False, 0, None

    def entry_wanted(j):
        if ne[j]:
            return 0
        if el[j] and ok_l[j]:
            return 1
        if es[j] and ok_s[j]:
            return -1
        return 0

    for j in range(n):
        if trad[j] and (p_exit or p_entry):
            if p_exit and pos != 0:
                reg.chiudi(ent_i, pos, entry, j, o[j], 'segnale')
                pos = 0
            if p_entry and pos == 0 and j >= t0:
                pos, entry, ent_i, peak = p_entry, o[j], j, o[j]
                sl = tp = None
                if stop_px is not None:
                    sl = stop_px[p_sig]
                elif stop_frac is not None:
                    sl = entry * (1 - stop_frac * pos)
                elif stop_dist is not None:
                    sl = entry - stop_dist * pos
                if tgt_px is not None:
                    tp = tgt_px[p_sig]
                elif tgt_frac is not None:
                    tp = entry * (1 + tgt_frac * pos)
                elif tgt_dist is not None:
                    tp = entry + tgt_dist * pos
            p_exit, p_entry = False, 0
        if pos != 0 and trad[j]:
            stop = sl
            if trail_dist is not None:
                ts = peak - trail_dist * pos
                stop = ts if stop is None else (max(stop, ts) if pos > 0 else min(stop, ts))
            if ft_trailing is not None:
                prof = (peak - entry) / entry * pos
                if (not ft_trailing.get('only_offset')) or prof >= ft_trailing['offset']:
                    dist = ft_trailing['positive'] if prof >= ft_trailing['offset'] else stop_frac
                    ts = peak * (1 - dist * pos)
                    stop = ts if stop is None else (max(stop, ts) if pos > 0 else min(stop, ts))
            target = tp
            if roi_keys:
                mins = (tt[j] - tt[ent_i]).total_seconds() / 60
                r = roi[[k for k in roi_keys if k <= mins][-1]]
                target = entry * (1 + r * pos)
            if stop is not None and ((l[j] <= stop) if pos > 0 else (h[j] >= stop)):
                gap = (o[j] <= stop) if pos > 0 else (o[j] >= stop)
                reg.chiudi(ent_i, pos, entry, j, o[j] if gap else stop, 'stop')
                pos = 0
            elif target is not None and ((h[j] >= target) if pos > 0 else (l[j] <= target)):
                if roi_keys:   # freqtrade: livello del ROI limitato dentro la candela
                    px = max(target, l[j]) if pos > 0 else min(target, h[j])
                else:          # ordine limite: se la candela apre oltre il target si esce all'apertura
                    px = max(target, o[j]) if pos > 0 else min(target, o[j])
                reg.chiudi(ent_i, pos, entry, j, px, 'target')
                pos = 0
            else:
                peak = max(peak, h[j]) if pos > 0 else min(peak, l[j])
            if pos != 0 and fc[j]:
                reg.chiudi(ent_i, pos, entry, j, c[j], 'orario')
                pos = 0
        if pos == 0:
            if not p_entry:
                w = entry_wanted(j)
                if w:
                    p_entry, p_sig = w, j
        elif not p_exit:
            ex = (pos > 0 and xl[j]) or (pos < 0 and xs[j])
            if ex and ignore_exit_if_entry and ((pos > 0 and el[j]) or (pos < 0 and es[j])):
                ex = False
            rev = reverse and ((pos > 0 and es[j]) or (pos < 0 and el[j]))
            if ex or rev:
                p_exit = True
                if rev and not ne[j] and (ok_s[j] if pos > 0 else ok_l[j]):
                    p_entry, p_sig = -pos, j
                elif same_bar:
                    w = entry_wanted(j)
                    if w:
                        p_entry, p_sig = w, j
    if pos != 0:
        reg.chiudi(ent_i, pos, entry, n - 1, c[-1], 'fine dati')
    return reg.df()


def comprare_e_tenere(base, start='2016-01-01'):
    x = base[base.index >= start]['close']
    return (x.iloc[-1] / x.iloc[0] - 1) * 100
