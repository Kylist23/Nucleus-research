"""Prova 3 - le 5 uscite di exit_simulator.py (skill exit-strategies, github.com/agiprolabs/claude-trading-skills,
commit 981e1d7) usate COSI' COME SONO su EUR/USD o Bitcoin. Stessa prova fatta sull'oro in
1_Bot/Prove_skill_esterne_2026-10-20/prova_exit_strategies.py: acquisto alla chiusura H1 che rompe il massimo
delle 24 H1 precedenti (rottura nuova); la skill compra soltanto e controlla gli stop sulle chiusure H1.
Costi (in % del prezzo): costo per operazione e swap del mercato (mercati.py), pagati 0, 1 e 2 volte.
Controllo: stesse uscite con entrate a caso (20 ripetizioni, stesso numero di segnali), costi doppi.
Uso: python3 t3_exit_strategies.py <EURUSD|BTC> <percorso exit_simulator.py>
"""
import importlib.util
import sys
import numpy as np
import pandas as pd
from mercati import load, resample

MKT = sys.argv[1]
spec = importlib.util.spec_from_file_location('exit_simulator', sys.argv[2])
ex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ex)

base, cfg = load(MKT)
h1 = resample(base, '1h').reset_index()
pc = h1.close.shift(1)
h1['tr'] = pd.concat([h1.high - h1.low, (h1.high - pc).abs(), (h1.low - pc).abs()], axis=1).max(axis=1)
h1['atr'] = h1.tr.rolling(ex.ATR_PERIOD).mean().bfill()
h1['ema'] = h1.close.ewm(span=ex.EMA_PERIOD, adjust=False).mean()
ch = h1.high.rolling(24).max().shift(1)
up = h1.close > ch
real_sig = (up & ~up.shift(1, fill_value=False)).values

STRATS = {
    'Stop fisso 10%': lambda df, e: ex.fixed_stop_loss(df, e, ex.FIXED_STOP_PCT),
    'Trailing ATR 2,5': lambda df, e: ex.atr_trailing_stop(df, e, ex.ATR_TRAIL_MULT),
    'Uscita a fette': lambda df, e: ex.scaled_exits(df, e, e * (1 - ex.FIXED_STOP_PCT), ex.SCALED_TARGETS_RR, ex.SCALED_SELL_PCTS),
    'Trailing EMA 20': lambda df, e: ex.ema_trailing(df, e, ex.EMA_CONSEC),
    'Stop a tempo 50 barre': lambda df, e: ex.time_stop(df, e, ex.TIME_STOP_BARS),
}
COLS = ['open', 'high', 'low', 'close', 'atr', 'ema']


def run(fn, sig):
    i, out = 30, []
    while i < len(h1) - 2:
        if not sig[i]:
            i += 1; continue
        entry = h1.close[i]
        df = h1.iloc[i + 1:i + 1 + ex.NUM_BARS][COLS].reset_index(drop=True)
        r = fn(df, entry)
        t_exit = h1.time[min(i + 1 + r['exit_bar'], len(h1) - 1)]
        nights = (t_exit.normalize() - h1.time[i].normalize()).days
        cost = h1.sp[i] / entry * 100 + cfg['swap_long'] * 100 * nights / 365
        out.append(dict(time=h1.time[i], pnl=r['pnl_pct'], cost=cost, reason=r['exit_reason'], bars=r['exit_bar'] + 1))
        i = i + 1 + r['exit_bar'] + 1
    return pd.DataFrame(out)


rows, ctrl = [], []
rng = np.random.default_rng(7)
for name, fn in STRATS.items():
    t = run(fn, real_sig)
    t['y'] = t.time.dt.year
    for cm in (0, 1, 2):
        net = t.pnl - cm * t.cost
        eq = (1 + net / 100).cumprod()
        rows.append(dict(uscita=name, costi=f'x{cm}', operazioni=len(t), vinte=f'{(net > 0).mean():.0%}',
                         somma_pct=round(net.sum(), 1), media_pct=round(net.mean(), 3),
                         p2016_19=round(net[t.y <= 2019].sum(), 1), p2020_22=round(net[t.y >= 2020].sum(), 1),
                         ultimo_terzo=round(net[t.time >= '2020-09-01'].sum(), 1),
                         drawdown_pct=round((1 - eq / eq.cummax()).max() * 100, 1), ore_medie=round(t.bars.mean(), 0),
                         motivo=t.reason.value_counts().index[0]))
    t.to_csv(f"../{MKT}/t3_exit_{name.split()[0].lower()}_{name.split()[-1].lower().replace(',', '')}.csv", index=False)
    real_net2 = (t.pnl - 2 * t.cost).sum()
    sums = []
    for rep in range(20):
        sig = np.zeros(len(h1), dtype=bool)
        sig[rng.choice(np.arange(30, len(h1) - 2), size=int(real_sig.sum()), replace=False)] = True
        r = run(fn, sig)
        sums.append((r.pnl - 2 * r.cost).sum())
    below = sum(s < real_net2 for s in sums)
    ctrl.append(f"{name}: reale {real_net2:+.1f}% | entrate a caso (20): mediana {np.median(sums):+.1f}%, "
                f"min {min(sums):+.1f}%, max {max(sums):+.1f}%, prove casuali sotto il reale: {below}/20")
res = pd.DataFrame(rows)
pd.set_option('display.width', 250)
print(f'{cfg["nome"]}, solo acquisti, somma dei rendimenti % delle operazioni (senza leva)')
print(res.to_string(index=False))
print()
print('\n'.join(ctrl))
print(f"\nRiferimento: comprare e tenere {cfg['nome']} dal primo all'ultimo prezzo H1 = "
      f"{(h1.close.iloc[-1] / h1.close.iloc[0] - 1) * 100:+.1f}%")
