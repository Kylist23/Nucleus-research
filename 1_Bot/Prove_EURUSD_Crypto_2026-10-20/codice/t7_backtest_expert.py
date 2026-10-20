"""Prova 7 - giudizio della skill backtest-expert (github.com/tradermonty/claude-trading-skills, commit cb0f3aa,
scripts/evaluate_backtest.py usato COSI' COM'E') sui risultati con costi doppi. Le prove in R sono convertite in %
con rischio 1% per operazione (come sull'oro). Limite di drawdown impostato al 10% come Nucleus.
Uso: python3 t7_backtest_expert.py <EURUSD|BTC> <percorso evaluate_backtest.py> nome=file.csv [nome=file.csv ...]
"""
import subprocess
import sys
from pathlib import Path
import pandas as pd

MKT, EV = sys.argv[1], sys.argv[2]
out_dir = Path(f'../{MKT}/t7_backtest_expert')
out_dir.mkdir(exist_ok=True)
for item in sys.argv[3:]:
    name, f = item.split('=', 1)
    t = pd.read_csv(f, parse_dates=['time'])
    if 'ret' in t.columns:
        net, npar = t.ret - 2 * t.cost, 4
    elif 'pnl' in t.columns:
        net, npar = t.pnl - 2 * t.cost, 3
    else:
        net, npar = t.R * 1.0, 5
    if len(net) < 1:
        continue
    w, l = net[net > 0], net[net <= 0]
    eq = (1 + net / 100).cumprod()
    dd = (1 - eq / eq.cummax()).max() * 100
    years = max(1, round((t.time.max() - t.time.min()).days / 365.25))
    args = ['python3', '-I', EV, '--total-trades', str(len(net)), '--win-rate', f'{len(w) / len(net) * 100:.2f}',
            '--avg-win-pct', f'{(w.mean() if len(w) else 0.0001):.4f}',
            '--avg-loss-pct', f'{(abs(l.mean()) if len(l) else 0.0001):.4f}',
            '--max-drawdown-pct', f'{min(dd, 99.9):.2f}', '--years-tested', str(years),
            '--num-parameters', str(npar), '--slippage-tested', '--max-acceptable-drawdown-pct', '10',
            '--output-dir', str(out_dir / name)]
    r = subprocess.run(args, capture_output=True, text=True)
    first = [x for x in (r.stdout + r.stderr).splitlines() if x and not x.startswith(('JSON', 'Markdown'))]
    print(f'== {name}: ' + ' | '.join(first))
