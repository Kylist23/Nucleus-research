//+------------------------------------------------------------------+
//|                                                NucleusEA_D1.mq5  |
//|                                                Progetto Nucleus  |
//+------------------------------------------------------------------+
//
// SERIE D, TENTATIVO 1: OBIETTIVO RADDOPPIO (idee provate in totale: 10)
//   Richiesta dell'autore (14/10/2026): provare a raddoppiare 10.000 euro
//   sullo storico dell'oro con un EA.
//
// REGOLA (fissata PRIMA del test, mai ottimizzata)
//   - Una volta al giorno, alla prima quotazione dopo l'01:00 server:
//     se l'ultima chiusura D1 completata e' sopra la media semplice a 200
//     giorni si sta comprati, se e' sotto si sta venduti.
//   - Dimensione fissata all'entrata: valore della posizione =
//     capitale x 25% / volatilita' annua (dev. standard dei rendimenti
//     giornalieri degli ultimi 60 giorni x radice di 252), massimo 3 volte
//     il capitale. Nessuno stop sul singolo trade: si gira al cambio.
//   - La posizione resta aperta di notte e nel fine settimana (paga swap).
//   - Stop di emergenza al 40% di drawdown (solo tester e demo).
//
// CRITERI (registrati nel Manuale il 14/10/2026 PRIMA del test)
//   XAUUSD 2016.01.01 - 2022.12.31, deposito 10000 EUR, leva 1:25.
//   Obiettivo: capitale finale >= 20000 EUR con costi doppi.
//   Criteri Nucleus: >= 100 operazioni; Risultato OnTester > 0; acquisti e
//   vendite positivi; 2016-2019 e 2020-2022 positivi; drawdown < 10%.
//   Risultato OnTester = profitto - (uno spread in piu' per operazione
//   + lo swap pagato una seconda volta + commissioni).
//
// SBLOCCO DELLO STOP DI EMERGENZA (solo su conto demo)
//   Strumenti > Variabili globali (F3): elimina NUCLEUS_EA_<magic>_HALT.
//+------------------------------------------------------------------+
#property copyright "Progetto Nucleus"
#property version   "1.00"
#property description "Serie D1: tendenza a 200 giorni con leva controllata (obiettivo raddoppio). Solo DEMO."

#include <Trade\Trade.mqh>

//--- REGOLE FISSE (non input: il tester ricorda i valori dei test precedenti)
#define EA_VERSION        "D1-1.00"
#define SMA_PERIOD        200
#define VOL_DAYS          60
#define VOL_TARGET        0.25
#define MAX_LEVERAGE      3.0
#define TRADE_HOUR_FROM   1      // prima ora utile (server)
#define TRADE_HOUR_TO     22     // ultima ora utile (dalle 23 alle 01 il broker non esegue)
#define HARD_MAX_DD_PCT   40.0
#define FIRST_YEAR        2000
#define MAX_YEARS         60

//--- INPUT -----------------------------------------------------------
input group "Rischio"
input double InpMaxDrawdownPct = 40.0;   // Drawdown per stop di emergenza (%, max 40)
input double InpMaxLots        = 5.0;    // Volume massimo assoluto (lotti)

input group "Sicurezza e registro"
input bool   InpAllowRealAccount = false;            // Consenti conto REALE (lasciare false)
input ulong  InpMagic            = 20261014;         // Numero identificativo dell'EA
input bool   InpLogToCSV         = true;             // Scrivi il registro CSV
input string InpLogName          = "Nucleus_EAD1v100"; // Prefisso del file di registro

//--- VARIABILI GLOBALI -----------------------------------------------
CTrade   trade;
int      hSMA = INVALID_HANDLE;
bool     g_isTester = false;
datetime g_lastDecisionDay = 0;
double   g_peakMem = 0.0;
bool     g_haltMem = false;
string   g_gvPeak = "", g_gvHalt = "", g_logFile = "";

double   g_bhStart = 0.0;
double   g_extraCost = 0.0, g_commissionSum = 0.0, g_swapNeg = 0.0;
int      g_trades[2];                    // 0 = acquisti, 1 = vendite
double   g_net[2];
double   g_netYear[MAX_YEARS];
int      g_skipOther = 0, g_skipMinVol = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   g_isTester = (bool)MQLInfoInteger(MQL_TESTER);

   if(InpMaxDrawdownPct <= 0.0 || InpMaxDrawdownPct > HARD_MAX_DD_PCT)
   { Print("ERRORE: drawdown massimo fuori dai limiti."); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxLots <= 0.0)
   { Print("ERRORE: volume massimo non valido."); return INIT_PARAMETERS_INCORRECT; }

   ENUM_ACCOUNT_TRADE_MODE accMode = (ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE);
   if(!g_isTester && accMode == ACCOUNT_TRADE_MODE_REAL && !InpAllowRealAccount)
   {
      Print("BLOCCO DI SICUREZZA: questo e' un conto REALE. L'EA non parte.");
      return INIT_FAILED;
   }

   hSMA = iMA(_Symbol, PERIOD_D1, SMA_PERIOD, 0, MODE_SMA, PRICE_CLOSE);
   if(hSMA == INVALID_HANDLE)
   { Print("ERRORE: impossibile creare la media mobile."); return INIT_FAILED; }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);

   g_gvPeak = "NUCLEUS_EA_" + IntegerToString((long)InpMagic) + "_PEAK";
   g_gvHalt = "NUCLEUS_EA_" + IntegerToString((long)InpMagic) + "_HALT";
   if(GetPeak() <= 0.0) SetPeak(AccountInfoDouble(ACCOUNT_EQUITY));

   g_logFile = "Nucleus\\" + InpLogName + "_" + ModeString() + "_" + _Symbol + ".csv";
   g_trades[0] = 0; g_trades[1] = 0; g_net[0] = 0.0; g_net[1] = 0.0;
   ArrayInitialize(g_netYear, 0.0);

   PrintFormat("Nucleus EA %s avviato su %s | modalita' %s | SMA %d giorni | volatilita' obiettivo %.0f%% su %d giorni | leva massima %.1f | stop di emergenza %.0f%% | registro %s",
               EA_VERSION, _Symbol, ModeString(), SMA_PERIOD, VOL_TARGET * 100.0, VOL_DAYS,
               MAX_LEVERAGE, InpMaxDrawdownPct, g_logFile);
   PrintFormat("Swap del simbolo (impostazioni attuali del broker): acquisti %.2f, vendite %.2f, modo %d",
               SymbolInfoDouble(_Symbol, SYMBOL_SWAP_LONG), SymbolInfoDouble(_Symbol, SYMBOL_SWAP_SHORT),
               (int)SymbolInfoInteger(_Symbol, SYMBOL_SWAP_MODE));
   if(IsHalted())
      Print("ATTENZIONE: stop di emergenza ATTIVO. Nessun nuovo trade finche' non viene sbloccato.");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   double net = g_isTester ? TesterStatistics(STAT_PROFIT) : g_net[0] + g_net[1];
   double stress = net - (g_extraCost + g_swapNeg + MathAbs(g_commissionSum));
   double bhEnd = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double bhPct = (g_bhStart > 0.0 && bhEnd > 0.0) ? (bhEnd / g_bhStart - 1.0) * 100.0 : 0.0;

   PrintFormat("RIEPILOGO D1 %s: acquisti %d (netto %.2f) | vendite %d (netto %.2f) | scartati: lotto minimo %d, altro %d",
               _Symbol, g_trades[0], g_net[0], g_trades[1], g_net[1], g_skipMinVol, g_skipOther);
   PrintFormat("RIEPILOGO D1 %s: netto %.2f | swap pagato %.2f | con costi raddoppiati (stima) %.2f | oro nel periodo %.2f%%",
               _Symbol, net, -g_swapNeg, stress, bhPct);
   for(int y = 0; y < MAX_YEARS; y++)
      if(g_netYear[y] != 0.0)
         PrintFormat("RIEPILOGO D1 %s anno %d: netto %.2f", _Symbol, FIRST_YEAR + y, g_netYear[y]);

   if(hSMA != INVALID_HANDLE) IndicatorRelease(hSMA);
   Comment("");
}

double OnTester()
{
   return TesterStatistics(STAT_PROFIT) - (g_extraCost + g_swapNeg + MathAbs(g_commissionSum));
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(g_bhStart <= 0.0) g_bhStart = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   UpdateRiskState();
   if(!g_isTester) ShowStatus();
   if(IsHalted()) return;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(dt.hour < TRADE_HOUR_FROM || dt.hour > TRADE_HOUR_TO) return;
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED)) return;

   //--- una decisione al giorno
   datetime day = TimeCurrent() - (TimeCurrent() % 86400);
   if(day == g_lastDecisionDay) return;
   g_lastDecisionDay = day;

   int want = Signal();
   if(want == 0) return;
   int have = PositionDir();
   if(have == want) return;
   if(have != 0) { CloseOurPositions(); if(PositionDir() != 0) return; }
   OpenPosition(want);
}

//--- +1 comprati, -1 venduti, 0 dati insufficienti
int Signal()
{
   double sma[];
   double cl[];
   if(CopyBuffer(hSMA, 0, 1, 1, sma) != 1 || sma[0] <= 0.0) return 0;
   if(CopyClose(_Symbol, PERIOD_D1, 1, 1, cl) != 1) return 0;
   if(cl[0] > sma[0]) return 1;
   if(cl[0] < sma[0]) return -1;
   return 0;
}

//--- volatilita' annua dai rendimenti giornalieri (barre D1 complete)
double AnnualVol()
{
   double c[];
   if(CopyClose(_Symbol, PERIOD_D1, 1, VOL_DAYS + 1, c) != VOL_DAYS + 1) return 0.0;
   double r[]; ArrayResize(r, VOL_DAYS);
   double m = 0.0;
   for(int k = 0; k < VOL_DAYS; k++) { r[k] = MathLog(c[k + 1] / c[k]); m += r[k]; }
   m /= VOL_DAYS;
   double s = 0.0;
   for(int k = 0; k < VOL_DAYS; k++) s += (r[k] - m) * (r[k] - m);
   return MathSqrt(s / (VOL_DAYS - 1)) * MathSqrt(252.0);
}

void OpenPosition(int dir)
{
   double vol = AnnualVol();
   if(vol <= 0.0) { g_skipOther++; return; }
   double lev = MathMin(VOL_TARGET / vol, MAX_LEVERAGE);

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick)) { g_skipOther++; return; }
   double price = (dir > 0) ? tick.ask : tick.bid;

   // valore di 1 lotto in valuta del conto = profitto per un movimento dell'1% x 100
   double p1 = 0.0;
   if(!OrderCalcProfit(ORDER_TYPE_BUY, _Symbol, 1.0, price, price * 1.01, p1) || p1 <= 0.0) { g_skipOther++; return; }
   double valuePerLot = p1 * 100.0;
   double notional = AccountInfoDouble(ACCOUNT_EQUITY) * lev;

   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(step <= 0.0) { g_skipOther++; return; }
   double lots = MathMin(notional / valuePerLot, MathMin(vmax, InpMaxLots));
   lots = MathFloor(lots / step + 1e-9) * step;
   if(lots < vmin) { g_skipMinVol++; return; }
   lots = NormalizeDouble(lots, (int)MathMax(0, MathRound(-MathLog10(step))));

   double margin = 0.0;
   ENUM_ORDER_TYPE type = (dir > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(!OrderCalcMargin(type, _Symbol, lots, price, margin) || margin > AccountInfoDouble(ACCOUNT_MARGIN_FREE) * 0.5)
   { g_skipOther++; return; }

   bool ok = (dir > 0) ? trade.Buy(lots, _Symbol, 0.0, 0.0, 0.0, "NucleusEA D1 acquisto")
                       : trade.Sell(lots, _Symbol, 0.0, 0.0, 0.0, "NucleusEA D1 vendita");
   uint rc = trade.ResultRetcode();
   if(!ok || (rc != TRADE_RETCODE_DONE && rc != TRADE_RETCODE_PLACED))
   { PrintFormat("Ordine NON eseguito: codice %u (%s)", rc, trade.ResultRetcodeDescription()); g_skipOther++; return; }
   PrintFormat("Entrata %s %.2f lotti | volatilita' %.1f%% | leva %.2f", dir > 0 ? "ACQUISTO" : "VENDITA", lots, vol * 100.0, lev);
}

//+------------------------------------------------------------------+
int PositionDir()
{
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      if(PositionGetTicket(k) == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol && (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
         return (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
   }
   return 0;
}

void CloseOurPositions()
{
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      ulong t = PositionGetTicket(k);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol && (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
         if(!trade.PositionClose(t))
            PrintFormat("ATTENZIONE: chiusura fallita (%s)", trade.ResultRetcodeDescription());
   }
}

//+------------------------------------------------------------------+
void UpdateRiskState()
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double peak = GetPeak();
   if(equity > peak) { SetPeak(equity); peak = equity; }
   if(!IsHalted() && peak > 0.0 && equity <= peak * (1.0 - InpMaxDrawdownPct / 100.0))
   {
      SetHalted();
      PrintFormat("STOP DI EMERGENZA: drawdown oltre il %.1f%% (picco %.2f, equity %.2f). Chiudo e mi fermo.",
                  InpMaxDrawdownPct, peak, equity);
      CloseOurPositions();
   }
}

double GetPeak()
{
   if(g_isTester) return g_peakMem;
   return GlobalVariableCheck(g_gvPeak) ? GlobalVariableGet(g_gvPeak) : 0.0;
}
void SetPeak(double v) { if(g_isTester) g_peakMem = v; else GlobalVariableSet(g_gvPeak, v); }
bool IsHalted()
{
   if(g_isTester) return g_haltMem;
   return (GlobalVariableCheck(g_gvHalt) && GlobalVariableGet(g_gvHalt) > 0.5);
}
void SetHalted() { if(g_isTester) g_haltMem = true; else GlobalVariableSet(g_gvHalt, 1.0); }

//+------------------------------------------------------------------+
//| Registro CSV e statistiche                                       |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   ulong deal = trans.deal;
   if(deal == 0) return;
   if(!HistoryDealSelect(deal))
   {
      HistorySelect(0, TimeCurrent() + 60);
      if(!HistoryDealSelect(deal)) return;
   }
   if(HistoryDealGetString(deal, DEAL_SYMBOL) != _Symbol) return;
   if((ulong)HistoryDealGetInteger(deal, DEAL_MAGIC) != InpMagic) return;

   long   dType  = HistoryDealGetInteger(deal, DEAL_TYPE);
   long   dEntry = HistoryDealGetInteger(deal, DEAL_ENTRY);
   double comm   = HistoryDealGetDouble(deal, DEAL_COMMISSION);
   double swap   = HistoryDealGetDouble(deal, DEAL_SWAP);
   double pnl    = HistoryDealGetDouble(deal, DEAL_PROFIT) + swap + comm;
   g_commissionSum += comm;
   if(swap < 0.0) g_swapNeg += -swap;          // lo swap come costo si paga una seconda volta

   int dirIdx = -1;
   if(dEntry == DEAL_ENTRY_IN)  dirIdx = (dType == DEAL_TYPE_BUY)  ? 0 : 1;
   if(dEntry == DEAL_ENTRY_OUT) dirIdx = (dType == DEAL_TYPE_SELL) ? 0 : 1;
   if(dirIdx >= 0)
   {
      g_net[dirIdx] += pnl;
      MqlDateTime dt;
      TimeToStruct((datetime)HistoryDealGetInteger(deal, DEAL_TIME), dt);
      int y = dt.year - FIRST_YEAR;
      if(y >= 0 && y < MAX_YEARS) g_netYear[y] += pnl;
   }
   if(dEntry == DEAL_ENTRY_IN && dirIdx >= 0)
   {
      g_trades[dirIdx]++;
      MqlTick tick;
      double sc = 0.0;
      double vol = HistoryDealGetDouble(deal, DEAL_VOLUME);
      if(SymbolInfoTick(_Symbol, tick) && OrderCalcProfit(ORDER_TYPE_BUY, _Symbol, vol, tick.ask, tick.bid, sc))
         g_extraCost += MathAbs(sc);           // uno spread in piu' per operazione
   }
   if(InpLogToCSV) WriteDealToCSV(deal);
}

void WriteDealToCSV(ulong deal)
{
   int h = FileOpen(g_logFile, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON | FILE_SHARE_READ, ',');
   if(h == INVALID_HANDLE)
   { PrintFormat("ATTENZIONE: impossibile aprire il registro %s (errore %d)", g_logFile, GetLastError()); return; }
   if(FileSize(h) == 0)
      FileWrite(h, "mode", "ea_version", "deal_ticket", "position_id", "server_time", "symbol",
                "deal_type", "entry", "reason", "volume", "price", "profit", "commission", "swap",
                "spread_points_at_log", "balance_after", "equity_at_log");
   FileSeek(h, 0, SEEK_END);

   long dType = HistoryDealGetInteger(deal, DEAL_TYPE);
   long dEntry = HistoryDealGetInteger(deal, DEAL_ENTRY);
   MqlTick tick;
   double spreadPts = -1.0;
   if(SymbolInfoTick(_Symbol, tick) && _Point > 0.0) spreadPts = (tick.ask - tick.bid) / _Point;

   FileWrite(h, ModeString(), EA_VERSION, IntegerToString((long)deal),
             IntegerToString(HistoryDealGetInteger(deal, DEAL_POSITION_ID)),
             TimeToString((datetime)HistoryDealGetInteger(deal, DEAL_TIME), TIME_DATE | TIME_SECONDS),
             _Symbol,
             (dType == DEAL_TYPE_BUY) ? "BUY" : (dType == DEAL_TYPE_SELL ? "SELL" : "OTHER"),
             (dEntry == DEAL_ENTRY_IN) ? "IN" : (dEntry == DEAL_ENTRY_OUT ? "OUT" : "OTHER"),
             EnumToString((ENUM_DEAL_REASON)HistoryDealGetInteger(deal, DEAL_REASON)),
             DoubleToString(HistoryDealGetDouble(deal, DEAL_VOLUME), 2),
             DoubleToString(HistoryDealGetDouble(deal, DEAL_PRICE), _Digits),
             DoubleToString(HistoryDealGetDouble(deal, DEAL_PROFIT), 2),
             DoubleToString(HistoryDealGetDouble(deal, DEAL_COMMISSION), 2),
             DoubleToString(HistoryDealGetDouble(deal, DEAL_SWAP), 2),
             DoubleToString(spreadPts, 1),
             DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2),
             DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2));
   FileClose(h);
}

//+------------------------------------------------------------------+
string ModeString()
{
   if(g_isTester) return "TESTER";
   ENUM_ACCOUNT_TRADE_MODE m = (ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE);
   if(m == ACCOUNT_TRADE_MODE_DEMO)    return "DEMO";
   if(m == ACCOUNT_TRADE_MODE_CONTEST) return "CONTEST";
   return "REAL";
}

void ShowStatus()
{
   int d = PositionDir();
   Comment(StringFormat("Nucleus EA %s  |  %s  |  %s\nStato: %s\nPosizione: %s\nEquity: %.2f   Picco: %.2f",
                        EA_VERSION, ModeString(), _Symbol,
                        IsHalted() ? "FERMO - stop di emergenza (sblocco manuale)" : "attivo",
                        d > 0 ? "comprati" : (d < 0 ? "venduti" : "nessuna"),
                        AccountInfoDouble(ACCOUNT_EQUITY), GetPeak()));
}
//+------------------------------------------------------------------+
