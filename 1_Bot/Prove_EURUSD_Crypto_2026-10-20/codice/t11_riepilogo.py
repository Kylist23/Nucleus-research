"""Riepilogo economico di tutte le prove della campagna EUR/USD e Bitcoin (fase 1 e fase 2), ricalcolato dai CSV
delle operazioni. Conto di riferimento: 10.000 euro.
  - prove in R (rischio fisso): 0,5% di rischio per operazione = 50 euro per R;
  - prove in % (tutto il capitale in ogni operazione, senza leva): 10.000 euro per operazione = 100 euro per 1%.
Nessun interesse composto negli euro: ogni operazione usa sempre la stessa cifra. "Peggior discesa" = la perdita
piu' grande dal punto piu' alto del conto, in euro, con costi doppi; "azzerato" = il conto scende a zero o sotto.
Le colonne "composto" reinvestono i guadagni (0,5% di rischio per le prove in R, tutto il capitale per le %). Criteri Nucleus ricalcolati con lo stesso
metodo delle prove (costi doppi; drawdown composto al 0,5% di rischio per le prove in R, senza leva per le %).
Uso: python3 t11_riepilogo.py   (scrive ../riepilogo_numeri.csv)
"""
from pathlib import Path
import numpy as np
import pandas as pd
from mercati import load_fase2

ROOT = Path(__file__).resolve().parent.parent
EURO_R, EURO_PCT, CONTO = 50.0, 100.0, 10_000.0

F1 = [('C1 candela avvolgente M15 con tendenza H1', 'Nucleus (serie C)', 't1_c1_operazioni.csv', None),
      ('E1 rottura di 24 ore con trailing', 'Nucleus (serie E)', 't2_serie_E1_operazioni.csv', None),
      ('E2 rottura di 24 ore con uscita a fette', 'Nucleus (serie E)', 't2_serie_E2_operazioni.csv', None),
      ('Controllo della serie E (target 2R)', 'Nucleus (serie E)', 't2_serie_CTRL_operazioni.csv', None),
      ('Uscita: stop fisso 10%', 'agiprolabs exit-strategies', 't3_exit_stop_10%.csv', None),
      ('Uscita: trailing ATR 2,5', 'agiprolabs exit-strategies', 't3_exit_trailing_25.csv', None),
      ('Uscita: a fette', 'agiprolabs exit-strategies', 't3_exit_uscita_fette.csv', None),
      ('Uscita: trailing EMA 20', 'agiprolabs exit-strategies', 't3_exit_trailing_20.csv', None),
      ('Uscita: stop a tempo 50 candele', 'agiprolabs exit-strategies', 't3_exit_stop_barre.csv', None),
      ('Candela a martello (solo forma)', 'tradermonty stockbee', 't4_martello_geometria.csv', None),
      ('FAdxSmaStrategy', 'freqtrade-strategies', 't5_freqtrade_FAdxSmaStrategy.csv', None),
      ('VolatilitySystem', 'freqtrade-strategies', 't5_freqtrade_VolatilitySystem.csv', None),
      ('TrendFollowingStrategy', 'freqtrade-strategies', 't5_freqtrade_TrendFollowingStrategy.csv', None),
      ('F apertura di New York', 'Nucleus (serie F)', 't6_FGH_operazioni.csv', 'F'),
      ('G dollaro BCE', 'Nucleus (serie G)', 't6_FGH_operazioni.csv', 'G'),
      ('H rimbalzo del giorno dopo', 'Nucleus (serie H)', 't6_FGH_operazioni.csv', 'H')]
REGIME = [('Skill regime-detection: medie 10/30 su H1', 't8_regime_H1_statica.csv'),
          ('Skill regime-detection: adattiva su H1', 't8_regime_H1_adattiva.csv'),
          ('Skill regime-detection: medie 10/30 giornaliere', 't8_regime_D1_statica.csv'),
          ('Skill regime-detection: adattiva giornaliera', 't8_regime_D1_adattiva.csv')]
N = [('N1', 'Inversione intraday', 'QuantConnect Lean'), ('N2', 'Bollinger + RSI + regime giornaliero', 'OptiFabian'),
     ('N3', 'HLHB (medie 5/10 + RSI + ADX)', 'BabyPips'), ('N4', 'Rottura di Londra', 'tradlysis'),
     ('N5', 'RSI2 di Connors', 'jesse'), ('N6', 'Dynamic Breakout II', 'QuantConnect Tutorials')]
K = [('K1', 'Donchian 20 + media 200', 'jesse'), ('K2', 'Rottura di volatilita (Larry Williams)', 'pyupbit-autotrade'),
     ('K2b', 'Rottura di volatilita + media 15', 'pyupbit-autotrade'), ('K3', 'RSI2 di Connors', 'jesse'),
     ('K4', 'BbandRsi', 'freqtrade-strategies'), ('K5', 'SimpleBollinger', 'jesse'), ('K6', 'TradingView_RSI', 'jesse'),
     ('K7', 'Supertrend', 'freqtrade-strategies'), ('K8', 'Incrocio medie 50/200', 'jesse')]


def misura(t):
    """Ritorna tipo, serie lorda, serie netta x1 e x2 nelle unita' della prova."""
    if 'R_lordo' in t.columns:
        return 'R', t.R_lordo, (t.R_lordo + t.R) / 2, t.R
    gross = t['ret'] if 'ret' in t.columns else t['pnl']
    return '%', gross, gross - t['cost'], gross - 2 * t['cost']


def riga(mkt, fase, prova, fonte, t, nota=''):
    t = t.copy()
    t['time'] = pd.to_datetime(t['time'])
    tipo, g, n1, n2 = misura(t)
    eur = EURO_R if tipo == 'R' else EURO_PCT
    y = t.time.dt.year
    longs, shorts = n2[t.dir > 0].sum(), n2[t.dir < 0].sum()
    p1, p2 = n2[y <= 2019].sum(), n2[y >= 2020].sum()
    eq = (1 + (0.005 * n2 if tipo == 'R' else n2 / 100)).cumprod()
    dd = (1 - eq / eq.cummax()).max() * 100 if len(t) else 0.0
    conto = CONTO + (n2 * eur).cumsum()
    discesa = float((np.maximum.accumulate(np.r_[CONTO, conto.to_numpy()]) - np.r_[CONTO, conto.to_numpy()]).max())
    azz1 = bool((CONTO + (n1 * eur).cumsum()).min() <= 0) if len(t) else False
    azz2 = bool(conto.min() <= 0) if len(t) else False
    k = 0.005 if tipo == 'R' else 0.01
    comp1 = ((1 + k * n1).cumprod().iloc[-1] - 1) * 100 if len(t) else 0.0
    comp2 = ((1 + k * n2).cumprod().iloc[-1] - 1) * 100 if len(t) else 0.0
    ok = [len(t) >= 100, n2.sum() > 0, longs > 0 and shorts > 0, p1 > 0 and p2 > 0, dd < 10]
    return dict(mercato=mkt, fase=fase, prova=prova, fonte=fonte, tipo=tipo, operazioni=len(t),
                acquisti=int((t.dir > 0).sum()), vendite=int((t.dir < 0).sum()),
                senza_costi=round(g.sum(), 1), costi_normali=round(n1.sum(), 1), costi_doppi=round(n2.sum(), 1),
                euro_senza_costi=round(g.sum() * eur), euro_costi_normali=round(n1.sum() * eur),
                euro_costi_doppi=round(n2.sum() * eur), peggior_discesa_euro=round(discesa),
                drawdown_pct=round(dd, 1), azzerato_costi_normali=azz1, azzerato_costi_doppi=azz2,
                composto_costi_normali_pct=round(comp1, 1), composto_costi_doppi_pct=round(comp2, 1),
                criteri=''.join('S' if x else 'N' for x in ok),
                verdetto='PASSA' if all(ok) else 'BOCCIATA', solo_acquisti=bool((t.dir > 0).all()), nota=nota)


rows = []
for mkt in ('EURUSD', 'BTC'):
    d = ROOT / mkt
    for prova, fonte, f, serie in F1:
        t = pd.read_csv(d / f)
        if serie:
            t = t[t.serie == serie]
        if 'dir' not in t.columns:
            t['dir'] = 1
        rows.append(riga(mkt, 1, prova, fonte, t))
    for prova, f in REGIME:
        rows.append(riga(mkt, 2, prova, 'agiprolabs regime-detection', pd.read_csv(d / f)))
    if mkt == 'EURUSD':
        for code, name, src in N:
            rows.append(riga(mkt, 2, f'{code} {name}', src, pd.read_csv(d / f't9_{code}.csv')))
            rows.append(riga(mkt, 2, f'{code} {name} + filtro regime', src + ' + regime-detection',
                             pd.read_csv(d / f't9_{code}_filtro.csv')))
    else:
        for code, name, src in K:
            rows.append(riga(mkt, 2, f'{code} {name}', src, pd.read_csv(d / f't10_{code}.csv')))
            rows.append(riga(mkt, 2, f'{code} {name} + filtro regime', src + ' + regime-detection',
                             pd.read_csv(d / f't10_{code}_filtro_a.csv')))
            rows.append(riga(mkt, 2, f'{code} {name} + filtro tendenza', src + ' + crypto-regime-analyzer',
                             pd.read_csv(d / f't10_{code}_filtro_b.csv')))

r = pd.DataFrame(rows)
r.to_csv(ROOT / 'riepilogo_numeri.csv', index=False)
pd.set_option('display.width', 250)
pd.set_option('display.max_rows', 200)
cols = ['mercato', 'fase', 'prova', 'tipo', 'operazioni', 'euro_senza_costi', 'euro_costi_normali', 'euro_costi_doppi',
        'peggior_discesa_euro', 'drawdown_pct', 'criteri', 'verdetto']
print(r[cols].to_string())
for mkt in ('EURUSD', 'BTC'):
    x = r[r.mercato == mkt]
    print(f"\n{mkt}: prove {len(x)}, passano {int((x.verdetto == 'PASSA').sum())}; "
          f"positive con costi normali {int((x.euro_costi_normali > 0).sum())}, con costi doppi {int((x.euro_costi_doppi > 0).sum())}; "
          f"positive senza costi {int((x.euro_senza_costi > 0).sum())}")
    print('   media euro (costi normali / doppi):', round(x.euro_costi_normali.mean()), '/', round(x.euro_costi_doppi.mean()))
    lv = x[~x.solo_acquisti]
    print(f"   prove con acquisti e vendite: {len(lv)}, positive con costi doppi {int((lv.euro_costi_doppi > 0).sum())}")
for mkt in ('EURUSD', 'BTC'):
    base, _ = load_fase2(mkt)
    c = base[base.index >= '2016-01-01'].close.resample('1D').last().dropna()
    dd = (1 - c / c.cummax()).max() * 100
    print(f"comprare e tenere {mkt}: {(c.iloc[-1] / c.iloc[0] - 1) * 100:+.1f}% ({(c.iloc[-1] / c.iloc[0] - 1) * CONTO:+,.0f} euro), "
          f"discesa massima {dd:.0f}% (picco {c.cummax().idxmax().date()}...)")
