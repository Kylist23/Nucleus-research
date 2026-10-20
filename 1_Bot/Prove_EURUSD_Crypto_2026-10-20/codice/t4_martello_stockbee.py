"""Prova 4 - candela a martello della skill stockbee-exhaustion-hammer-screener (github.com/tradermonty/
claude-trading-skills, commit cb0f3aa), funzione analyze_symbol usata COSI' COM'E' con le soglie predefinite,
sulle candele giornaliere di EUR/USD (lun-ven) o Bitcoin (7 giorni su 7). Stessa prova fatta sull'oro in
1_Bot/Prove_skill_esterne_2026-10-20/prova_hammer_stockbee.py: entrata alla chiusura del giorno del martello,
stop = stop_reference della skill, uscita alla chiusura del 5o giorno se lo stop non scatta prima. Solo acquisti.
Variante "solo geometria": solo la forma della candela. Costi del mercato pagati 0, 1 e 2 volte. Risultati in R.
Uso: python3 t4_martello_stockbee.py <EURUSD|BTC> <percorso screen_exhaustion_hammer.py>
"""
import importlib.util
import sys
import numpy as np
import pandas as pd
from mercati import load, swap_cost

MKT, SKILL_PATH = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location('hammer', SKILL_PATH)
hm = importlib.util.module_from_spec(spec)
sys.modules['hammer'] = hm
spec.loader.exec_module(hm)
sys.argv = [sys.argv[0]]
args = hm.parse_arguments()

base, cfg = load(MKT)
d1 = base.resample('1D').agg(dict(open='first', high='max', low='min', close='last', volume='sum',
                                  sp='median')).dropna(subset=['open'])
if MKT == 'EURUSD':
    d1 = d1[d1.index.dayofweek < 5]
d1 = d1.reset_index()


def bars_at(i):
    w = d1.iloc[max(0, i - 119):i + 1][::-1]
    return [hm.Bar(date=str(r.time.date()), open=r.open, high=r.high, low=r.low, close=r.close,
                   volume=int(r.volume)) for r in w.itertuples()]


def geometry_only(res):
    bad = {'lower_wick_too_small', 'body_too_large', 'weak_close_location', 'weak_wick_body_asymmetry'}
    return not (bad & set(res.get('reject_reasons', [])))


def trade(i, stop):
    entry = d1.close[i]
    dist = entry - stop
    for k in range(i + 1, min(i + 6, len(d1))):
        if d1.open[k] <= stop:
            return k, (d1.open[k] - entry) / dist, dist
        if d1.low[k] <= stop:
            return k, -1.0, dist
    k = min(i + 5, len(d1) - 1)
    return k, (d1.close[k] - entry) / dist, dist


states, sel, reasons = {}, {'skill': [], 'geometria': []}, {}
for i in range(130, len(d1) - 1):
    res = hm.analyze_symbol(MKT, bars_at(i), args)
    states[res['state']] = states.get(res['state'], 0) + 1
    for r in res.get('reject_reasons', []):
        reasons[r] = reasons.get(r, 0) + 1
    if res['state'] != 'REJECTED':
        sel['skill'].append((i, res['stop_reference']))
    if geometry_only(res) and 'stop_reference' in res:
        sel['geometria'].append((i, res['stop_reference']))

print(f"{cfg['nome']} - stati restituiti dalla skill:", states)
print('Motivi di scarto piu frequenti:', dict(sorted(reasons.items(), key=lambda x: -x[1])[:8]))
for name, lst in sel.items():
    out, free = [], 0
    for i, stop in lst:
        if i < free or stop >= d1.close[i]:
            continue
        k, r, dist = trade(i, stop)
        nights = (d1.time[k] - d1.time[i]).days
        cost = (d1.sp[i] + swap_cost(cfg, 1, d1.close[i], nights)) / dist
        out.append(dict(time=d1.time[i], dir=1, R_lordo=r, cost=cost))
        free = k + 1
    t = pd.DataFrame(out)
    if t.empty:
        print(f'{name}: nessuna operazione'); continue
    t['y'] = t.time.dt.year
    for cm in (0, 1, 2):
        net = t.R_lordo - cm * t.cost
        eq = (1 + 0.005 * net).cumprod()
        print(f"{name} costi x{cm}: operazioni={len(t)} vinte={(net > 0).mean():.0%} totale={net.sum():+.1f}R "
              f"media={net.mean():+.3f}R 2016-19={net[t.y <= 2019].sum():+.1f}R 2020-22={net[t.y >= 2020].sum():+.1f}R "
              f"ultimo_terzo={net[t.time >= '2020-09-01'].sum():+.1f}R drawdown={(1 - eq / eq.cummax()).max():.1%}")
    t['R'] = t.R_lordo - 2 * t.cost
    t.to_csv(f'../{MKT}/t4_martello_{name}.csv', index=False)
