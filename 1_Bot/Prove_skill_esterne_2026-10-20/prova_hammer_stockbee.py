"""Prova esplorativa (non e' un tentativo Nucleus): filtro "exhaustion hammer" della skill
stockbee-exhaustion-hammer-screener (github.com/tradermonty/claude-trading-skills, commit cb0f3aa),
usato COSI' COM'E' (funzione analyze_symbol, soglie predefinite) sulle candele giornaliere dell'oro.
Ogni giorno si passano alla funzione le ultime 120 candele; il segnale e' ogni giorno non scartato.
La skill non opera e non da' un'uscita precisa: il suo modello e' "stop al minimo del giorno, poi revisione
a 3-5 giorni". Qui: entrata alla chiusura del giorno del martello, stop = stop_reference della skill,
uscita alla chiusura del 5o giorno se lo stop non scatta prima (se lo stop e' toccato si esce allo stop,
o all'apertura se il prezzo apre sotto). Solo acquisti, come la skill.
Variante "solo geometria": stessa forma di candela (coda lunga, corpo piccolo, chiusura in alto), senza i filtri
pensati per le azioni (ribasso minimo del 6%, recupero del 2% dal minimo).
Costi: spread (minimo 0,20 $) e swap stimato (acquisti 3%/anno) pagati 0, 1 e 2 volte. Risultati in R.
Uso: python3 -I prova_hammer_stockbee.py <screen_exhaustion_hammer.py> <XAUUSD_M5.csv>
"""
import importlib.util
import sys
import numpy as np
import pandas as pd

SKILL_PATH, M5_PATH = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location('hammer', SKILL_PATH)
hm = importlib.util.module_from_spec(spec)
sys.modules['hammer'] = hm
spec.loader.exec_module(hm)
sys.argv = [sys.argv[0]]
args = hm.parse_arguments()           # soglie predefinite della skill

m5 = pd.read_csv(M5_PATH)
m5['time'] = pd.to_datetime(m5['time'], format='%Y.%m.%d %H:%M')
m5 = m5[m5.time >= '2016-01-01'].set_index('time').sort_index()
m5['sp'] = m5.spread_points * 0.01
d1 = m5.resample('1D').agg(dict(open='first', high='max', low='min', close='last', tick_volume='sum',
                                 sp='median')).dropna(subset=['open'])
d1 = d1[d1.index.dayofweek < 5].reset_index()


def bars_at(i):
    w = d1.iloc[max(0, i - 119):i + 1][::-1]
    return [hm.Bar(date=str(r.time.date()), open=r.open, high=r.high, low=r.low, close=r.close,
                   volume=int(r.tick_volume)) for r in w.itertuples()]


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


states, sel = {}, {'skill': [], 'geometria': []}
reasons = {}
for i in range(130, len(d1) - 1):
    res = hm.analyze_symbol('XAUUSD', bars_at(i), args)
    states[res['state']] = states.get(res['state'], 0) + 1
    for r in res.get('reject_reasons', []):
        reasons[r] = reasons.get(r, 0) + 1
    if res['state'] != 'REJECTED':
        sel['skill'].append((i, res['stop_reference']))
    if geometry_only(res) and 'stop_reference' in res:
        sel['geometria'].append((i, res['stop_reference']))

print('Stati restituiti dalla skill:', states)
print('Motivi di scarto piu frequenti:', dict(sorted(reasons.items(), key=lambda x: -x[1])[:8]))
for name, lst in sel.items():
    out, free = [], 0
    for i, stop in lst:
        if i < free:
            continue
        k, r, dist = trade(i, stop)
        nights = (d1.time[k] - d1.time[i]).days
        cost = (max(d1.sp[i], 0.20) + 0.03 * d1.close[i] * nights / 365) / dist
        out.append(dict(time=d1.time[i], R=r, cost=cost))
        free = k + 1
    t = pd.DataFrame(out)
    if t.empty:
        print(f'{name}: nessuna operazione'); continue
    t['y'] = t.time.dt.year
    for cm in (0, 1, 2):
        net = t.R - cm * t.cost
        print(f"{name} costi x{cm}: operazioni={len(t)} vinte={(net > 0).mean():.0%} totale={net.sum():+.1f}R "
              f"media={net.mean():+.3f}R 2016-19={net[t.y <= 2019].sum():+.1f}R 2020-22={net[t.y >= 2020].sum():+.1f}R")
    t.to_csv(f'hammer_{name}.csv', index=False)
