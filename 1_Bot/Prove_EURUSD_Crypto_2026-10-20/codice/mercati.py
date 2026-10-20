"""Caricamento dei dati e ipotesi sui costi per le prove su EUR/USD e Bitcoin (Progetto Nucleus, 20/10/2026).

Ogni prova chiama load(mercato) e riceve:
  - un DataFrame con indice 'time' (ora server = New York + 7 ore, come il broker dell'autore) e colonne
    open, high, low, close, volume, sp (costo di andata e ritorno in unita' di prezzo, pagato UNA volta);
  - un dizionario con le ipotesi del mercato (costi, swap, ore senza esecuzione, granularita' delle candele).
I costi delle prove vengono poi pagati DUE volte, come nelle prove sull'oro.

EUR/USD: M15 (non c'e' M5 gratuito raggiungibile), da github.com/ejtraderLabs/historical-data (commit fbd29b3,
  licenza Apache 2.0), finisce il 04/03/2022. Costo 1,5 pip per operazione (spread + commissione di un conto ECN).
  Swap stimato: acquisti 2,5%/anno, vendite 0,5%/anno (tassi USA piu' alti di quelli europei, piu' il ricarico).
  Nessuna esecuzione 23:00-00:59 server (cambio di giorno, spread larghi), come sull'oro.
BTC/USD: M5 ricavato dal minuto di Bitstamp, da github.com/ff137/bitstamp-btcusd-minute-data (commit c711b69,
  dati derivati da "Zielak (mczielinski), Bitcoin Historical Data, Kaggle", licenza CC BY-SA 4.0).
  Costo 0,20% del prezzo per operazione (commissioni dell'exchange o spread di un CFD); swap/finanziamento
  stimato: acquisti 10%/anno, vendite 5%/anno. Si scambia 24 ore su 24, 7 giorni su 7: nessuna fascia esclusa.
Periodo comune: 2016-01-01 -> 2022-12-31 (EUR/USD fino al 04/03/2022). La cassaforte dal 2023 non e' nei file.
"""
from pathlib import Path
import pandas as pd

DATI = Path(__file__).resolve().parent.parent / 'Dati'

CONFIG = {
    'EURUSD': dict(file='EURUSD_M15_2015-12_2022-03.csv', tf=15, swap_long=0.025, swap_short=0.005,
                   cost_fixed=0.00015, cost_pct=0.0, no_trade_hours=(23, 0), fine='2022-03-04',
                   nome='EUR/USD'),
    'BTC': dict(file='BTCUSD_M5_2015-12_2022-12.csv', tf=5, swap_long=0.10, swap_short=0.05,
                cost_fixed=0.0, cost_pct=0.0020, no_trade_hours=(), fine='2022-12-31', nome='Bitcoin'),
}


def load(market, start='2016-01-01', warmup_days=0):
    cfg = dict(CONFIG[market])
    df = pd.read_csv(DATI / cfg['file'])
    df['time'] = pd.to_datetime(df['time'], format='%Y.%m.%d %H:%M')
    if 'tick_volume' in df.columns:
        df = df.rename(columns={'tick_volume': 'volume'})
    t0 = pd.Timestamp(start) - pd.Timedelta(days=warmup_days)
    df = df[(df.time >= t0) & (df.time < '2023-01-01')].set_index('time').sort_index()
    df['sp'] = cfg['cost_fixed'] + cfg['cost_pct'] * df['close']
    cfg['market'] = market
    return df, cfg


def resample(df, rule):
    out = df.resample(rule, label='left', closed='left').agg(
        dict(open='first', high='max', low='min', close='last', volume='sum', sp='median'))
    return out.dropna(subset=['open'])


def swap_cost(cfg, d, price, nights):
    """Swap stimato per una posizione tenuta 'nights' notti di calendario (unita' di prezzo, pagato una volta)."""
    return (cfg['swap_long'] if d > 0 else cfg['swap_short']) * price * nights / 365


def summary(t, rcol='R', label=''):
    """Riepilogo con il metro Nucleus. t ha colonne time, dir, R (netto con costi doppi), R_lordo."""
    t = t.copy()
    t['y'] = t.time.dt.year
    L, S = t[t.dir > 0][rcol].sum(), t[t.dir < 0][rcol].sum()
    p1, p2 = t[t.y <= 2019][rcol].sum(), t[t.y >= 2020][rcol].sum()
    last3 = t[t.time >= '2020-09-01'][rcol].sum()
    eq = (1 + 0.005 * t[rcol]).cumprod()
    dd = (1 - eq / eq.cummax()).max() if len(t) else 0.0
    ok = [len(t) >= 100, t[rcol].sum() > 0, L > 0 and S > 0, p1 > 0 and p2 > 0, dd < 0.10]
    line = (f"{label}: n={len(t)} (acq {int((t.dir > 0).sum())}, ven {int((t.dir < 0).sum())}) "
            f"vinte={(t[rcol] > 0).mean():.0%} costi_doppi={t[rcol].sum():+.1f}R senza_costi={t.R_lordo.sum():+.1f}R "
            f"media={t[rcol].mean():+.3f}R acquisti={L:+.1f}R vendite={S:+.1f}R 2016-19={p1:+.1f}R "
            f"2020-22={p2:+.1f}R ultimo_terzo={last3:+.1f}R drawdown={dd:.1%} "
            f"criteri={''.join('S' if c else 'N' for c in ok)} -> {'PASSA' if all(ok) else 'BOCCIATA'}")
    per_year = t.groupby('y')[rcol].sum().round(1).to_dict()
    return line, per_year, all(ok), dict(n=len(t), net=t[rcol].sum(), gross=t.R_lordo.sum(), longs=L, shorts=S,
                                         p1=p1, p2=p2, last3=last3, dd=dd, passed=all(ok))


# Fase 2 (strategie di altri repository): stessi costi, un anno in piu' di storia solo per il riscaldamento degli
# indicatori (le operazioni partono comunque dal 2016-01-01). Bitcoin qui e' in ora UTC, come le candele dei
# repository crypto (giorno UTC, candele da 3 e 6 ore allineate a UTC); EUR/USD resta in ora server.
FASE2 = {
    'EURUSD': dict(file='EURUSD_M15_2015-01_2022-03.csv', ora='server'),
    'BTC': dict(file='BTCUSD_M5_UTC_2015-01_2022-12.csv', ora='UTC'),
}


def load_fase2(market):
    cfg = dict(CONFIG[market])
    cfg.update(FASE2[market])
    df = pd.read_csv(DATI / cfg['file'])
    df['time'] = pd.to_datetime(df['time'], format='%Y.%m.%d %H:%M')
    if 'tick_volume' in df.columns:
        df = df.rename(columns={'tick_volume': 'volume'})
    df = df[df.time < '2023-01-01'].set_index('time').sort_index()
    df['sp'] = cfg['cost_fixed'] + cfg['cost_pct'] * df['close']
    cfg['market'] = market
    return df, cfg
