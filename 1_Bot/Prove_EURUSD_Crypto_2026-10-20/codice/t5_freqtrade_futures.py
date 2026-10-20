"""Prova 5 - tre strategie "futures" di freqtrade-strategies (github.com/freqtrade/freqtrade-strategies, commit
f3340ce, GPL-3), che comprano e vendono allo scoperto, su EUR/USD o Bitcoin. Stesse regole della prova sull'oro
(1_Bot/Prove_skill_esterne_2026-10-20/prova_freqtrade_futures.py), valori predefiniti, leva tolta:
  FAdxSmaStrategy (H1), VolatilitySystem (candele da 3 ore), TrendFollowingStrategy (M5; su EUR/USD M15,
  perche' non ci sono dati M5).
Uso: python3 t5_freqtrade_futures.py <EURUSD|BTC>
"""
import sys
import numpy as np
from mercati import load, resample
from ft_common import adx_ta, atr_ta, crossed_above, crossed_below, simulate, report

MKT = sys.argv[1]
base, cfg = load(MKT, warmup_days=20)


def bars(rule):
    b = base if rule is None else resample(base, rule)
    return b.reset_index()


out = []
d = bars('1h')
adx = adx_ta(d, 14)
s12, s48 = d.close.rolling(12).mean(), d.close.rolling(48).mean()
el = ((adx > 30) & crossed_above(s12, s48)).values
es = ((adx > 30) & crossed_below(s12, s48)).values
x = (adx < 30).values
res = {'FAdxSmaStrategy (H1)': simulate(d, cfg, el, es, x, x, 0.05, {0: 0.05, 30: 0.10, 60: 0.075})}

d = bars('3h')
atr2 = atr_ta(d, 14) * 2.0
chg = d.close.diff()
el = (chg > atr2.shift(1)).values
es = (-chg > atr2.shift(1)).values
res['VolatilitySystem (3 ore)'] = simulate(d, cfg, el, es, es, el, 1.0, {0: 100.0}, reverse=True)

d = bars(None)
obv = (np.sign(d.close.diff()).fillna(0) * d.volume).cumsum()
ema = d.close.ewm(span=20, adjust=False).mean()
el = ((d.close > ema) & (d.close.shift(1) <= ema.shift(1)) & (obv > obv.shift(1))).values
es = ((d.close < ema) & (d.close.shift(1) >= ema.shift(1)) & (obv < obv.shift(1))).values
xl = ((d.close < ema) & (d.close.shift(1) >= ema.shift(1)) & (obv > obv.shift(1))).values
xs = ((d.close > ema) & (d.close.shift(1) <= ema.shift(1)) & (obv < obv.shift(1))).values
tf = 'M15' if cfg['tf'] == 15 else 'M5'
res[f'TrendFollowingStrategy ({tf})'] = simulate(d, cfg, el, es, xl, xs, 0.265, {0: 0.15, 30: 0.10, 60: 0.05},
                                                 trailing=dict(positive=0.05, offset=0.10, only_offset=False))

print(f"{cfg['nome']}: somma dei rendimenti % delle operazioni, senza leva")
for name, t in res.items():
    lines, tt = report(name, t)
    print('\n'.join(lines))
    if tt is not None:
        tt.to_csv(f"../{MKT}/t5_freqtrade_{name.split()[0]}.csv", index=False)
