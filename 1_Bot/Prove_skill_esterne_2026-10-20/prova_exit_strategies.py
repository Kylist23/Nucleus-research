"""Prova esplorativa (non e' un tentativo Nucleus): le 5 uscite di exit_simulator.py della skill
exit-strategies (github.com/agiprolabs/claude-trading-skills, commit 981e1d7) usate COSI' COME SONO,
ma su prezzi veri dell'oro invece che su prezzi inventati.
Entrata: acquisto alla chiusura H1 che rompe il massimo delle 24 H1 precedenti (rottura nuova, come la Serie E).
Le funzioni della skill gestiscono solo acquisti e controllano gli stop solo sulle chiusure H1, senza costi.
Il programma riporta il risultato "come la skill" (senza costi) e poi con spread vero (minimo 0,20 $) e swap stimato
(acquisti 3%/anno, notti di calendario) pagati 1 e 2 volte. Controllo: le stesse uscite con entrate a caso (20 ripetizioni).
Uso: python3 -I prova_exit_strategies.py <exit_simulator.py> <XAUUSD_M5.csv>
"""
import importlib.util
import sys
import numpy as np
import pandas as pd

spec = importlib.util.spec_from_file_location('exit_simulator', sys.argv[1])
ex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ex)

m5 = pd.read_csv(sys.argv[2])
m5['time'] = pd.to_datetime(m5['time'], format='%Y.%m.%d %H:%M')
m5 = m5[m5.time >= '2016-01-01'].set_index('time').sort_index()
m5['sp'] = m5.spread_points * 0.01
h1 = m5.resample('1h', label='left', closed='left').agg(
    dict(open='first', high='max', low='min', close='last', sp='median')).dropna(subset=['open']).reset_index()
# ATR ed EMA calcolati come in generate_price_series della skill
pc = h1.close.shift(1)
h1['tr'] = pd.concat([h1.high - h1.low, (h1.high - pc).abs(), (h1.low - pc).abs()], axis=1).max(axis=1)
h1['atr'] = h1.tr.rolling(ex.ATR_PERIOD).mean().bfill()
h1['ema'] = h1.close.ewm(span=ex.EMA_PERIOD, adjust=False).mean()
ch = h1.high.rolling(24).max().shift(1)
up = h1.close > ch
sig = (up & ~up.shift(1, fill_value=False)).values

STRATS = {
    'Stop fisso 10%': lambda df, e: ex.fixed_stop_loss(df, e, ex.FIXED_STOP_PCT),
    'Trailing ATR 2,5': lambda df, e: ex.atr_trailing_stop(df, e, ex.ATR_TRAIL_MULT),
    'Uscita a fette': lambda df, e: ex.scaled_exits(df, e, e * (1 - ex.FIXED_STOP_PCT), ex.SCALED_TARGETS_RR, ex.SCALED_SELL_PCTS),
    'Trailing EMA 20': lambda df, e: ex.ema_trailing(df, e, ex.EMA_CONSEC),
    'Stop a tempo 50 barre': lambda df, e: ex.time_stop(df, e, ex.TIME_STOP_BARS),
}
rows = []
for name, fn in STRATS.items():
    i, out = 30, []
    while i < len(h1) - 2:
        if not sig[i]:
            i += 1; continue
        entry = h1.close[i]
        df = h1.iloc[i + 1:i + 1 + ex.NUM_BARS][['open', 'high', 'low', 'close', 'atr', 'ema']].reset_index(drop=True)
        r = fn(df, entry)
        sp = max(h1.sp[i], 0.20)
        t_exit = h1.time[min(i + 1 + r['exit_bar'], len(h1) - 1)]
        nights = (t_exit.normalize() - h1.time[i].normalize()).days
        out.append(dict(time=h1.time[i], pnl=r['pnl_pct'], cost=sp / entry * 100 + 3.0 * nights / 365,
                        reason=r['exit_reason'], bars=r['exit_bar'] + 1, nights=nights))
        i = i + 1 + r['exit_bar'] + 1
    t = pd.DataFrame(out)
    t['y'] = t.time.dt.year
    for cm in (0, 1, 2):
        net = t.pnl - cm * t.cost
        rows.append(dict(uscita=name, costi=f'x{cm}', operazioni=len(t), vinte=f'{(net > 0).mean():.0%}',
                         somma_pct=round(net.sum(), 1), media_pct=round(net.mean(), 3),
                         p2016_19=round(net[t.y <= 2019].sum(), 1), p2020_22=round(net[t.y >= 2020].sum(), 1),
                         ore_medie=round(t.bars.mean(), 0),
                         motivo_piu_frequente=t.reason.value_counts().index[0]))
    t.to_csv(f'exit_strategies_{name.split()[0].lower()}_{name.split()[-1].lower()}.csv', index=False)
res = pd.DataFrame(rows)
# controllo: entrate a caso (stesso numero di segnali), solo per le due uscite con piu' operazioni
rng = np.random.default_rng(7)
ctrl = []
real_sig = sig.copy()
for name in ('Trailing ATR 2,5', 'Trailing EMA 20'):
    sums = []
    for rep in range(20):
        sig = np.zeros(len(h1), dtype=bool)
        sig[rng.choice(np.arange(30, len(h1) - 2), size=int(real_sig.sum()), replace=False)] = True
        i, tot = 30, 0.0
        while i < len(h1) - 2:
            if not sig[i]:
                i += 1; continue
            entry = h1.close[i]
            df = h1.iloc[i + 1:i + 1 + ex.NUM_BARS][['open', 'high', 'low', 'close', 'atr', 'ema']].reset_index(drop=True)
            r = STRATS[name](df, entry)
            t_exit = h1.time[min(i + 1 + r['exit_bar'], len(h1) - 1)]
            nights = (t_exit.normalize() - h1.time[i].normalize()).days
            tot += r['pnl_pct'] - 2 * (max(h1.sp[i], 0.20) / entry * 100 + 3.0 * nights / 365)
            i = i + 1 + r['exit_bar'] + 1
        sums.append(tot)
    ctrl.append(f"{name}: entrate a caso, costi x2, somma % su 20 ripetizioni: mediana {np.median(sums):+.1f}, "
                f"min {min(sums):+.1f}, max {max(sums):+.1f}")
sig = real_sig
pd.set_option('display.width', 250)
print(res.to_string(index=False))
print()
print('\n'.join(ctrl))
print('\nRiferimento: comprare e tenere l\'oro dal primo all\'ultimo prezzo H1 =',
      f"{(h1.close.iloc[-1] / h1.close.iloc[0] - 1) * 100:+.1f}%")
