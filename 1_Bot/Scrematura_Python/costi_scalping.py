"""Quanto pesano i costi (spread pagato due volte) su target piccoli? (14/10/2026)
Analisi descrittiva, NON e' un test di strategia e non conta come tentativo.
Uso: python3 costi_scalping.py ../Dati/XAUUSD_M5_2016-2022.csv
"""
import pandas as pd, sys
df = pd.read_csv(sys.argv[1]); df['time'] = pd.to_datetime(df.time, format='%Y.%m.%d %H:%M')
df = df[(df.time >= '2016-01-01') & (df.time.dt.hour >= 1) & (df.time.dt.hour <= 22)]
df['sp'] = df.spread_points * 0.01; df['rng'] = df.high - df.low
print('spread mediano $', df.sp.median(), '| 90 percentile $', df.sp.quantile(.9), '| range M5 mediano $', round(df.rng.median(), 2))
g = df.groupby(df.time.dt.hour).agg(sp=('sp', 'median'), rng=('rng', 'median'))
g['costo2x_su_range_%'] = (2 * g.sp / g.rng * 100).round(0); print(g.round(2).to_string())
print(df.groupby(df.time.dt.year).agg(sp=('sp', 'median'), rng=('rng', 'median')).round(2))
c = 2 * df.sp.median()
for t in [0.5, 1, 2, 3, 5]:
    print(f'target=stop=${t}: costo 2x = {c/t*100:.0f}% del target, operazioni vinte necessarie per pareggiare = {(t+c)/(2*t)*100:.0f}%')
