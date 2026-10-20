"""Prova 8 - skill regime-detection (github.com/agiprolabs/claude-trading-skills, commit 981e1d7,
scripts/regime_backtest.py) usata COSI' COM'E' su prezzi veri di EUR/USD o Bitcoin, su candele H1 e D1.
La skill confronta due strategie (solo acquisti):
  - statica: incrocio delle medie esponenziali 10 e 30 (compra quando la 10 sale sopra la 30, vende quando scende);
  - adattiva: se l'ADX(14) e' sopra 22 usa l'incrocio delle medie, altrimenti l'RSI(14) (compra sotto 35, vende
    sopra 65); dimensione ridotta quando la volatilita' (percentile dell'ATR su 80 candele) e' sopra 0,65.
Le funzioni della skill eseguono al prezzo di chiusura della candela del segnale (come nel codice originale).
Dal registro delle operazioni della skill ricavo il rendimento % di ogni operazione (moltiplicato per la quota
investita) e tolgo i costi del mercato (mercati.py) pagati 0, 1 e 2 volte; la commissione interna della skill
(10 punti base) non viene usata.
Fa parte della fase 2 (prova (c) registrata il 20/10/2026 alle 17:05 UTC): dati di mercati.load_fase2, operazioni
dal 2016-01-01.
Uso: python3 t8_regime_detection.py <EURUSD|BTC> <percorso regime_backtest.py>
"""
import importlib.util
import sys
import pandas as pd
from mercati import load_fase2, resample, swap_cost

MKT = sys.argv[1]
spec = importlib.util.spec_from_file_location('regime_backtest', sys.argv[2])
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)

base, cfg = load_fase2(MKT)          # un anno di storia in piu' per il riscaldamento; Bitcoin in ora UTC


def trades_from_log(log, df, adaptive):
    out, buy = [], None
    for _, r in log.iterrows():
        if r['action'] == 'BUY':
            buy = r
        elif str(r['action']).startswith('SELL') and buy is not None:
            i, j = int(buy['bar']), int(r['bar'])
            t0, t1 = df.index[i], df.index[j]
            q = float(buy.get('size_mult', 1.0)) if adaptive else 1.0
            ret = (r['price'] / buy['price'] - 1) * 100 * q
            nights = (t1.normalize() - t0.normalize()).days
            cost = (df.sp.iloc[i] + swap_cost(cfg, 1, buy['price'], nights)) / buy['price'] * 100 * q
            out.append(dict(time=t0, dir=1, ret=ret, cost=cost, regime=buy.get('regime', ''), quota=q))
            buy = None
    t = pd.DataFrame(out)
    return t[t.time >= '2016-01-01'].reset_index(drop=True) if len(t) else t


print(f"{cfg['nome']} - skill regime-detection, solo acquisti, somma dei rendimenti % (senza leva)")
for tf, rule in (('H1', '1h'), ('D1', '1D')):
    df = resample(base, rule)
    if rule == '1D' and MKT == 'EURUSD':
        df = df[df.index.dayofweek < 5]
    vol_pct = rb.compute_atr_percentile(df['high'], df['low'], df['close'], rb.ATR_PERIOD, rb.VOL_LOOKBACK)
    adx = rb.compute_adx(df['high'], df['low'], df['close'], rb.ADX_PERIOD)
    rsi = rb.compute_rsi(df['close'], rb.RSI_PERIOD)
    log_s, _ = rb.run_static_strategy(df)
    log_a, _ = rb.run_adaptive_strategy(df, vol_pct, adx, rsi)
    for name, log, ad in (('statica (medie 10/30)', log_s, False), ('adattiva (medie o RSI)', log_a, True)):
        t = trades_from_log(log, df, ad)
        if t.empty:
            print(f'{tf} {name}: nessuna operazione'); continue
        t['y'] = t.time.dt.year
        for cm in (0, 1, 2):
            net = t.ret - cm * t.cost
            eq = (1 + net / 100).cumprod()
            dd = (1 - eq / eq.cummax()).max() * 100
            line = (f"{tf} {name} costi x{cm}: operazioni={len(t)} vinte={(net > 0).mean():.0%} totale={net.sum():+.1f}% "
                    f"2016-19={net[t.y <= 2019].sum():+.1f}% 2020-22={net[t.y >= 2020].sum():+.1f}% "
                    f"ultimo_terzo={net[t.time >= '2020-09-01'].sum():+.1f}% drawdown={dd:.1f}%")
            if cm == 2:
                ok = [len(t) >= 100, net.sum() > 0, False, net[t.y <= 2019].sum() > 0 and net[t.y >= 2020].sum() > 0, dd < 10]
                line += f" criteri={''.join('S' if x else 'N' for x in ok)} (solo acquisti: il criterio vendite non e' verificabile)"
            print(line)
        t.to_csv(f"../{MKT}/t8_regime_{tf}_{name.split()[0]}.csv", index=False)
bh = base[base.index >= '2016-01-01'].close
print(f"Riferimento: comprare e tenere {cfg['nome']} = {(bh.iloc[-1] / bh.iloc[0] - 1) * 100:+.1f}%")
