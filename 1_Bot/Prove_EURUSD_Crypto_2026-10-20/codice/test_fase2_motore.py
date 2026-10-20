"""Prove del simulatore della fase 2 (fase2_motore.py) su candele inventate: entrata all'apertura successiva,
stop controllato prima del target, gap oltre lo stop, ordini sospesi nelle ore senza esecuzione, ROI e trailing
di freqtrade, giorno precedente per i filtri. Uso: python3 test_fase2_motore.py. Ogni riga stampa il risultato
di un caso, da confrontare con il valore atteso scritto nel commento accanto (controllati il 20/10/2026); il caso 8
si ferma con un errore se il supertrend non coincide con la versione di riferimento."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np, pandas as pd
from fase2_motore import run_signals, run_target, supertrend_dir, punteggio_tendenza_btc, giorno_prima

cfg = dict(no_trade_hours=(23, 0), swap_long=0.0, swap_short=0.0)
def bars(rows, start='2016-01-04 20:00', freq='1h'):
    idx = pd.date_range(start, periods=len(rows), freq=freq)
    b = pd.DataFrame(rows, columns=['open', 'high', 'low', 'close'], index=idx)
    b['sp'] = 0.0; return b
Z = lambda n: np.zeros(n, bool)

# 1) entry next open, stop first within bar, gap through stop -> exit at open
b = bars([[100,101,99,100],[100,101,99,100],[100,100,90,95],[95,96,94,95]], start='2016-01-04 10:00')
el = np.array([1,0,0,0],bool)
t = run_signals(b, cfg, el, Z(4), Z(4), Z(4), stop_frac=0.05, tgt_frac=0.0001)
print('1', t[['time','entry','exit','motivo']].values.tolist())   # target 100.01 hit on bar1 (high 101) -> target at max(100.01, open 100)=100.01
t = run_signals(b, cfg, el, Z(4), Z(4), Z(4), stop_frac=0.05, tgt_frac=0.5)
print('1b', t[['entry','exit','motivo']].values.tolist())         # stop 95 on bar2 (low 90) -> 95
b2 = bars([[100,101,99,100],[100,101,99,100],[90,92,88,91],[95,96,94,95]], start='2016-01-04 10:00')
t = run_signals(b2, cfg, el, Z(4), Z(4), Z(4), stop_frac=0.05, tgt_frac=0.5)
print('1c', t[['entry','exit','motivo']].values.tolist())         # gap open 90 < stop 95 -> exit 90

# 2) signal at 22:00 bar -> no trading at 23:00 and 00:00 -> fill at 01:00 open
b = bars([[1,1,1,1],[2,2,2,2],[3,3,3,3],[4,4,4,4],[5,5,5,5]], start='2016-01-04 22:00')
t = run_signals(b, cfg, np.array([1,0,0,0,0],bool), Z(5), Z(5), Z(5))
print('2', t[['time','entry','motivo']].values.tolist())          # entry at 01:00 open=4, closed at end 5

# 3) reverse with filter blocking the short: exit only
b = bars([[1,1,1,1]]*6, start='2016-01-04 10:00')
el = np.array([1,0,0,0,0,0],bool); es = np.array([0,0,1,0,0,0],bool)
t = run_signals(b, cfg, el, es, Z(6), Z(6), reverse=True)
print('3a', t[['time','dir','motivo']].values.tolist())
t = run_signals(b, cfg, el, es, Z(6), Z(6), reverse=True, ok_s=np.zeros(6,bool))
print('3b', t[['time','dir','motivo']].values.tolist())

# 4) trailing in price units and flat_close
rows = [[100,100,100,100],[100,103,100,103],[103,106,103,106],[106,106,103.5,104],[104,104,104,104]]
b = bars(rows, start='2016-01-04 10:00')
t = run_signals(b, cfg, np.array([1,0,0,0,0],bool), Z(5), Z(5), Z(5), trail_dist=2.0)
print('4', t[['entry','exit','motivo']].values.tolist())          # peak 106 after bar2 -> stop 104 on bar3 (low 103.5) -> exit 104
fc = np.array([0,0,1,0,0],bool)
t = run_signals(b, cfg, np.array([1,0,0,0,0],bool), Z(5), Z(5), Z(5), trail_dist=2.0, flat_close=fc)
print('4b', t[['entry','exit','motivo']].values.tolist())         # flat at close of bar2 = 106

# 5) ROI freqtrade: {0:0.10}, candle low above target -> fill at low (clamped)
rows = [[100,100,100,100],[100,100,100,100],[115,120,112,118]]
b = bars(rows, start='2016-01-04 10:00')
t = run_signals(b, cfg, np.array([1,0,0],bool), Z(3), Z(3), Z(3), stop_frac=0.25, roi={0:0.10})
print('5', t[['entry','exit','motivo']].values.tolist())          # 112

# 6) run_target with flat_close
b = bars([[1,1,1,1],[2,2,2,2],[3,3,3,3],[4,4,4,4]], start='2016-01-04 20:00')
t = run_target(b, cfg, np.array([1,1,0,0]), flat_close=np.array([0,0,1,0],bool))
print('6', t[['time','entry','exit','motivo']].values.tolist())   # enter 21:00 open 2, close at 22:00 close 3

# 7) same_bar re-entry (jesse): exit long and enter short decided on the same bar
b = bars([[1,1,1,1]]*5, start='2016-01-04 10:00')
el = np.array([1,0,0,0,0],bool); es = np.array([0,0,1,0,0],bool); xl = np.array([0,0,1,0,0],bool)
t = run_signals(b, cfg, el, es, xl, Z(5), same_bar=True)
print('7', t[['time','dir','motivo']].values.tolist())

# 8) supertrend sanity vs a straightforward re-implementation of technical's code
rng = np.random.default_rng(0); c = 100 + np.cumsum(rng.normal(0, 1, 500))
d = pd.DataFrame({'open': c, 'high': c + rng.uniform(0, 1, 500), 'low': c - rng.uniform(0, 1, 500), 'close': c + rng.normal(0, .3, 500)})
def st_ref(df, m, p):
    tr = pd.concat([df.high-df.low,(df.high-df.close.shift()).abs(),(df.low-df.close.shift()).abs()],axis=1).max(axis=1); tr.iloc[0]=np.nan
    atr = tr.rolling(p).mean(); bub=(df.high+df.low)/2+m*atr; blb=(df.high+df.low)/2-m*atr
    n=len(df); fub=np.zeros(n); flb=np.zeros(n)
    for i in range(p,n):
        fub[i]=bub[i] if bub[i]<fub[i-1] or df.close.iat[i-1]>fub[i-1] else fub[i-1]
        flb[i]=blb[i] if blb[i]>flb[i-1] or df.close.iat[i-1]<flb[i-1] else flb[i-1]
    st=np.zeros(n)
    for i in range(p,n):
        st[i]= fub[i] if st[i-1]==fub[i-1] and df.close.iat[i]<=fub[i] else flb[i] if st[i-1]==fub[i-1] and df.close.iat[i]>fub[i] else flb[i] if st[i-1]==flb[i-1] and df.close.iat[i]>=flb[i] else fub[i] if st[i-1]==flb[i-1] and df.close.iat[i]<flb[i] else 0.0
    return np.where(st>0, np.where(df.close<st,'down','up'), None)
for m, p in ((4,8),(7,9),(1,8),(1,16),(3,18),(6,18)):
    a = supertrend_dir(d, m, p); r = st_ref(d, m, p)
    rr = np.array([1 if x=='up' else -1 if x=='down' else 0 for x in r])
    assert (a == rr).all(), (m, p)
print('8 supertrend identical to reference on 6 settings')

# 9) giorno_prima: bars of day D see day D-1
f = pd.DataFrame({'v':[1.,2.,3.]}, index=pd.to_datetime(['2016-01-04','2016-01-05','2016-01-06']))
idx = pd.to_datetime(['2016-01-04 05:00','2016-01-05 00:00','2016-01-05 23:45','2016-01-07 10:00'])
print('9', giorno_prima(f, idx).v.tolist())   # [nan, 1, 1, 3]
