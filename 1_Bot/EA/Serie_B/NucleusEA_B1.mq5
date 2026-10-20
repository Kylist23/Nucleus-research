//+------------------------------------------------------------------+
//|                                                NucleusEA_B1.mq5  |
//|                                                Progetto Nucleus  |
//+------------------------------------------------------------------+
//
// SERIE B, TENTATIVO 1 (idee provate in totale: 4)
//   Serie A (tendenza) chiusa dopo 3 tentativi bocciati.
//
// IDEA (presa dall'EA "H4 Zone Retest M5" trovato su GitHub, corretta)
//   Il massimo e il minimo del giorno precedente sono livelli guardati da
//   molti operatori. Quando una candela a 5 minuti li rompe con decisione,
//   il prezzo spesso torna a toccarli ("retest") prima di proseguire.
//   Si entra con un ordine limite proprio sul livello rotto.
//
// REGOLE
//   - Livelli: massimo e minimo del giorno precedente (D1).
//   - Rottura: candela M5 CHIUSA che apre dentro il livello e chiude oltre,
//     con corpo almeno pari al 50% della candela.
//   - Filtro di tendenza: chiusura H1 precedente sopra EMA 50 e EMA 200
//     per gli acquisti, sotto entrambe per le vendite.
//   - Entrata: ordine limite sul livello rotto, valido fino a fine sessione.
//   - Stop 1,5 x ATR(14) H1, target 3 x ATR(14) H1 (valori dell'originale).
//   - Sessione 7-22 (ora server), una posizione alla volta, al massimo
//     un tentativo per direzione al giorno. Chiusura il venerdi' sera.
//
// DIFFERENZE RISPETTO ALL'ORIGINALE (decise PRIMA del test)
//   - Acquisti E vendite (l'originale aveva le vendite disattivate).
//   - Indicatori creati una volta all'avvio (l'originale li leggeva
//     prima che fossero pronti).
//   - Nessun trailing e nessun breakeven in punti fissi.
//   - Nessun filtro notizie (non funziona nello Strategy Tester).
//   - Tutte le protezioni Nucleus.
//
// CRITERI DI VALUTAZIONE (registrati nel manuale PRIMA del test)
//   XAUUSD, 2016.01.01 - 2022.12.31. Cassaforte 2023-oggi intatta.
//   1. Almeno 100 operazioni.
//   2. Risultato dell'OnTester (costi raddoppiati) maggiore di zero.
//   3. Profitto netto positivo sia sugli acquisti sia sulle vendite.
//   4. Profitto netto positivo sia nel 2016-2019 sia nel 2020-2022.
//   5. Drawdown relativo dell'equity sotto il 10%.
//   Il confronto con il buy-and-hold dell'oro viene riportato, ma non e'
//   un criterio: la strategia non tiene esposizione a lungo termine.
//
// SBLOCCO DELLO STOP DI EMERGENZA (solo su conto demo)
//   Strumenti > Variabili globali (F3): elimina NUCLEUS_EA_<magic>_HALT.
//+------------------------------------------------------------------+
#property copyright "Progetto Nucleus"
#property version   "1.00"
#property description "Serie B1: rottura e retest dei livelli del giorno precedente. Solo DEMO."

#include <Trade\Trade.mqh>

//--- LIMITI RIGIDI --------------------------------------------------
#define HARD_MAX_RISK_PCT        1.0
#define HARD_MAX_DAILY_LOSS_PCT  3.0
#define HARD_MAX_DRAWDOWN_PCT   15.0
#define EA_VERSION              "B1-1.00"
#define FIRST_YEAR               2000
#define MAX_YEARS                60

//--- INPUT -----------------------------------------------------------
input group "Strategia (valori dell'EA originale, non ottimizzati)"
input double InpBodyPct       = 50.0;  // Corpo minimo della candela di rottura (% della candela)
input bool   InpUseEMAFilter  = true;  // Filtro di tendenza con le EMA su H1
input int    InpEMAFast       = 50;    // EMA veloce (H1)
input int    InpEMASlow       = 200;   // EMA lenta (H1)
input int    InpATRPeriod     = 14;    // Periodo ATR (H1)
input double InpSL_ATR        = 1.5;   // Stop = ATR x questo valore
input double InpTP_ATR        = 3.0;   // Target = ATR x questo valore
input int    InpSessionStart  = 7;     // Inizio sessione (ora server, inclusa)
input int    InpSessionEnd    = 23;    // Fine sessione (ora server, esclusa: 23 = fino alle 22:59)

input group "Rischio"
input double InpRiskPct         = 0.5;  // Rischio per operazione (% saldo, max 1.0)
input double InpMaxDailyLossPct = 2.0;  // Perdita giornaliera massima (%, max 3.0)
input double InpMaxDrawdownPct  = 10.0; // Drawdown per stop di emergenza (%, max 15)
input double InpMaxLots         = 1.0;  // Volume massimo assoluto (lotti)
input double InpMaxSpreadPctOfSL = 10.0;// Spread massimo (% della distanza dello stop)

input group "Fine settimana"
input bool   InpCloseBeforeWeekend = true; // Chiudi tutto il venerdi' sera
input int    InpFridayCloseHour    = 20;   // Ora di chiusura del venerdi' (server)

input group "Sicurezza e registro"
input bool   InpAllowRealAccount = false;          // Consenti conto REALE (lasciare false)
input ulong  InpMagic            = 20260927;       // Numero identificativo dell'EA
input bool   InpLogToCSV         = true;           // Scrivi il registro CSV
input string InpLogPrefix        = "Nucleus_EAB1"; // Prefisso del file di registro

//--- VARIABILI GLOBALI -----------------------------------------------
CTrade   trade;
int      hATR = INVALID_HANDLE, hFast = INVALID_HANDLE, hSlow = INVALID_HANDLE;

bool     g_isTester = false;
datetime g_zoneDay = 0;
double   g_zoneHigh = 0.0, g_zoneLow = 0.0;
bool     g_longUsed = false, g_shortUsed = false;
datetime g_lastM5 = 0;

datetime g_currentDay = 0;
double   g_dayStartEquity = 0.0, g_peakMem = 0.0;
bool     g_haltMem = false;
string   g_gvPeak = "", g_gvHalt = "", g_logFile = "";

double   g_bhStart = 0.0;               // prezzo iniziale per il buy-and-hold
double   g_extraCost = 0.0, g_commissionSum = 0.0;
int      g_trades[2];                   // 0 = acquisti, 1 = vendite
double   g_net[2];
double   g_netYear[MAX_YEARS];
int      g_setups = 0, g_noRetest = 0, g_skipMinVol = 0, g_skipAtLevel = 0;
int      g_skipSpread = 0, g_skipOther = 0;

//+------------------------------------------------------------------+
//| Avvio                                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   g_isTester = (bool)MQLInfoInteger(MQL_TESTER);

   if(InpRiskPct <= 0.0 || InpRiskPct > HARD_MAX_RISK_PCT)
   { Print("ERRORE: rischio per operazione fuori dai limiti."); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxDailyLossPct <= 0.0 || InpMaxDailyLossPct > HARD_MAX_DAILY_LOSS_PCT)
   { Print("ERRORE: perdita giornaliera fuori dai limiti."); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxDrawdownPct <= 0.0 || InpMaxDrawdownPct > HARD_MAX_DRAWDOWN_PCT)
   { Print("ERRORE: drawdown massimo fuori dai limiti."); return INIT_PARAMETERS_INCORRECT; }
   if(InpBodyPct <= 0.0 || InpBodyPct > 100.0 || InpSL_ATR <= 0.0 || InpTP_ATR <= 0.0 || InpATRPeriod <= 0)
   { Print("ERRORE: parametri della strategia non validi."); return INIT_PARAMETERS_INCORRECT; }
   if(!(InpEMAFast > 0 && InpEMAFast < InpEMASlow))
   { Print("ERRORE: deve valere 0 < EMA veloce < EMA lenta."); return INIT_PARAMETERS_INCORRECT; }
   if(InpSessionStart < 0 || InpSessionEnd > 24 || InpSessionStart >= InpSessionEnd)
   { Print("ERRORE: orari di sessione non validi."); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxLots <= 0.0 || InpMaxSpreadPctOfSL <= 0.0 || InpMaxSpreadPctOfSL > 25.0)
   { Print("ERRORE: volume massimo o filtro spread non validi."); return INIT_PARAMETERS_INCORRECT; }

   ENUM_ACCOUNT_TRADE_MODE accMode = (ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE);
   if(!g_isTester && accMode == ACCOUNT_TRADE_MODE_REAL && !InpAllowRealAccount)
   {
      Print("BLOCCO DI SICUREZZA: questo e' un conto REALE. L'EA non parte.");
      return INIT_FAILED;
   }

   //--- Indicatori creati UNA volta sola
   hATR  = iATR(_Symbol, PERIOD_H1, InpATRPeriod);
   hFast = iMA(_Symbol, PERIOD_H1, InpEMAFast, 0, MODE_EMA, PRICE_CLOSE);
   hSlow = iMA(_Symbol, PERIOD_H1, InpEMASlow, 0, MODE_EMA, PRICE_CLOSE);
   if(hATR == INVALID_HANDLE || hFast == INVALID_HANDLE || hSlow == INVALID_HANDLE)
   { Print("ERRORE: impossibile creare gli indicatori."); return INIT_FAILED; }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);

   g_gvPeak = "NUCLEUS_EA_" + IntegerToString((long)InpMagic) + "_PEAK";
   g_gvHalt = "NUCLEUS_EA_" + IntegerToString((long)InpMagic) + "_HALT";
   if(GetPeak() <= 0.0) SetPeak(AccountInfoDouble(ACCOUNT_EQUITY));

   g_logFile = "Nucleus\\" + InpLogPrefix + "_" + ModeString() + "_" + _Symbol + ".csv";

   g_trades[0] = 0; g_trades[1] = 0; g_net[0] = 0.0; g_net[1] = 0.0;
   ArrayInitialize(g_netYear, 0.0);

   g_lastM5 = iTime(_Symbol, PERIOD_M5, 0);   // si parte dalla prossima candela M5

   PrintFormat("Nucleus EA %s avviato su %s | modalita' %s | rischio %.2f%% | registro %s",
               EA_VERSION, _Symbol, ModeString(), InpRiskPct, g_logFile);
   if(IsHalted())
      Print("ATTENZIONE: stop di emergenza ATTIVO. Nessun nuovo trade finche' non viene sbloccato.");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Chiusura e riepilogo                                             |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   double net = g_isTester ? TesterStatistics(STAT_PROFIT) : g_net[0] + g_net[1];
   double stress = net - (g_extraCost + MathAbs(g_commissionSum));

   PrintFormat("RIEPILOGO B1 %s: rotture %d | ordini senza retest %d | scartati: lotto minimo %d, prezzo gia' al livello %d, spread %d, altro %d",
               _Symbol, g_setups, g_noRetest, g_skipMinVol, g_skipAtLevel, g_skipSpread, g_skipOther);
   PrintFormat("RIEPILOGO B1 %s: acquisti %d (netto %.2f) | vendite %d (netto %.2f)",
               _Symbol, g_trades[0], g_net[0], g_trades[1], g_net[1]);

   double bhEnd = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double bhPct = (g_bhStart > 0.0 && bhEnd > 0.0) ? (bhEnd / g_bhStart - 1.0) * 100.0 : 0.0;
   PrintFormat("RIEPILOGO B1 %s: netto %.2f | con costi raddoppiati (stima) %.2f | buy-and-hold nel periodo %.2f%%",
               _Symbol, net, stress, bhPct);

   for(int y = 0; y < MAX_YEARS; y++)
      if(g_netYear[y] != 0.0)
         PrintFormat("RIEPILOGO B1 %s anno %d: netto %.2f", _Symbol, FIRST_YEAR + y, g_netYear[y]);

   if(hATR  != INVALID_HANDLE) IndicatorRelease(hATR);
   if(hFast != INVALID_HANDLE) IndicatorRelease(hFast);
   if(hSlow != INVALID_HANDLE) IndicatorRelease(hSlow);
   Comment("");
}

double OnTester()
{
   return TesterStatistics(STAT_PROFIT) - (g_extraCost + MathAbs(g_commissionSum));
}

//+------------------------------------------------------------------+
//| Ciclo principale                                                 |
//+------------------------------------------------------------------+
void OnTick()
{
   if(g_bhStart <= 0.0) g_bhStart = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   UpdateRiskState();
   if(!g_isTester) ShowStatus();
   if(IsHalted()) { DeleteOurPendings(false); return; }

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);

   //--- Venerdi' sera: si chiude tutto
   if(InpCloseBeforeWeekend && dt.day_of_week == 5 && dt.hour >= InpFridayCloseHour)
   {
      DeleteOurPendings(true);
      if(HasOpenPosition()) CloseOurPositions();
      return;
   }

   //--- Nuovo giorno: nuovi livelli, ordini del giorno prima annullati
   datetime d0 = iTime(_Symbol, PERIOD_D1, 0);
   if(d0 != 0 && d0 != g_zoneDay)
   {
      DeleteOurPendings(true);
      double hi = iHigh(_Symbol, PERIOD_D1, 1);
      double lo = iLow(_Symbol, PERIOD_D1, 1);
      if(hi > 0.0 && lo > 0.0 && hi > lo)
      {
         g_zoneDay = d0; g_zoneHigh = hi; g_zoneLow = lo;
         g_longUsed = false; g_shortUsed = false;
      }
   }
   if(g_zoneHigh <= 0.0 || g_zoneLow <= 0.0) return;

   //--- Una valutazione per candela M5 chiusa
   datetime m5 = iTime(_Symbol, PERIOD_M5, 0);
   if(m5 == 0 || m5 == g_lastM5) return;
   g_lastM5 = m5;

   //--- Fuori sessione: nessun nuovo ordine, quelli in attesa si annullano
   bool inSession = (dt.day_of_week >= 1 && dt.day_of_week <= 5 &&
                     dt.hour >= InpSessionStart && dt.hour < InpSessionEnd);
   if(!inSession) { DeleteOurPendings(true); return; }

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED)) return;
   if(DailyLimitHit() || HasOpenPosition() || HasPendingOrder()) return;

   double o = iOpen(_Symbol, PERIOD_M5, 1), c = iClose(_Symbol, PERIOD_M5, 1);
   double h = iHigh(_Symbol, PERIOD_M5, 1), l = iLow(_Symbol, PERIOD_M5, 1);
   double range = h - l;
   if(range <= 0.0) return;
   bool bodyOk = (MathAbs(c - o) >= InpBodyPct / 100.0 * range);
   if(!bodyOk) return;

   if(!g_longUsed && o <= g_zoneHigh && c > g_zoneHigh && TrendOK(1))
   {
      g_longUsed = true; g_setups++;
      PlaceLimit(1, g_zoneHigh);
   }
   else if(!g_shortUsed && o >= g_zoneLow && c < g_zoneLow && TrendOK(-1))
   {
      g_shortUsed = true; g_setups++;
      PlaceLimit(-1, g_zoneLow);
   }
}

//--- Filtro di tendenza su candela H1 chiusa
bool TrendOK(int dir)
{
   if(!InpUseEMAFilter) return true;
   double f[], s[];
   if(CopyBuffer(hFast, 0, 1, 1, f) != 1 || CopyBuffer(hSlow, 0, 1, 1, s) != 1) return false;
   double c1 = iClose(_Symbol, PERIOD_H1, 1);
   if(c1 <= 0.0 || f[0] <= 0.0 || s[0] <= 0.0) return false;   // dati non pronti: nessuna entrata
   if(dir > 0) return (c1 > f[0] && c1 > s[0]);
   return (c1 < f[0] && c1 < s[0]);
}

//+------------------------------------------------------------------+
//| Ordine limite sul livello rotto                                  |
//+------------------------------------------------------------------+
void PlaceLimit(int dir, double level)
{
   double atr[];
   if(CopyBuffer(hATR, 0, 1, 1, atr) != 1 || atr[0] <= 0.0) { g_skipOther++; return; }

   double slDist  = atr[0] * InpSL_ATR;
   double tpDist  = atr[0] * InpTP_ATR;
   double minDist = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick)) { g_skipOther++; return; }

   double spread = tick.ask - tick.bid;
   if(spread < 0.0 || spread > slDist * InpMaxSpreadPctOfSL / 100.0) { g_skipSpread++; return; }

   double entry = NormalizePrice(level);

   //--- Il prezzo deve essere ancora oltre il livello, altrimenti niente retest da aspettare
   if(dir > 0 && tick.ask <= entry + minDist) { g_skipAtLevel++; return; }
   if(dir < 0 && tick.bid >= entry - minDist) { g_skipAtLevel++; return; }

   double sl = NormalizePrice(dir > 0 ? entry - slDist : entry + slDist);
   double tp = NormalizePrice(dir > 0 ? entry + tpDist : entry - tpDist);
   if(slDist <= minDist || tpDist <= minDist) { g_skipOther++; return; }

   double vol = CalcVolume(dir, entry, sl);
   if(vol <= 0.0) return;
   if(!MarginOK(dir, vol, entry)) { g_skipOther++; return; }

   bool ok = (dir > 0)
             ? trade.BuyLimit(vol, entry, _Symbol, sl, tp, ORDER_TIME_GTC, 0, "NucleusEA B1")
             : trade.SellLimit(vol, entry, _Symbol, sl, tp, ORDER_TIME_GTC, 0, "NucleusEA B1");
   uint rc = trade.ResultRetcode();
   if(!ok || (rc != TRADE_RETCODE_DONE && rc != TRADE_RETCODE_PLACED))
   {
      PrintFormat("Ordine limite NON inserito: codice %u (%s)", rc, trade.ResultRetcodeDescription());
      g_skipOther++;
   }
}

double NormalizePrice(double p)
{
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(ts > 0.0) p = MathRound(p / ts) * ts;
   return NormalizeDouble(p, _Digits);
}

//--- Volume in base al rischio: arrotondato SEMPRE per difetto
double CalcVolume(int dir, double price, double sl)
{
   double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPct / 100.0;
   ENUM_ORDER_TYPE type = (dir > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double pnl = 0.0;
   if(!OrderCalcProfit(type, _Symbol, 1.0, price, sl, pnl)) { g_skipOther++; return 0.0; }
   double lossPerLot = MathAbs(pnl);
   if(lossPerLot <= 0.0) { g_skipOther++; return 0.0; }

   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(step <= 0.0) { g_skipOther++; return 0.0; }

   double vol = riskMoney / lossPerLot;
   vol = MathMin(vol, MathMin(vmax, InpMaxLots));
   vol = MathFloor(vol / step + 1e-9) * step;
   if(vol < vmin) { g_skipMinVol++; return 0.0; }
   int vdigits = (int)MathMax(0, MathRound(-MathLog10(step)));
   return NormalizeDouble(vol, vdigits);
}

bool MarginOK(int dir, double vol, double price)
{
   ENUM_ORDER_TYPE type = (dir > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double margin = 0.0;
   if(!OrderCalcMargin(type, _Symbol, vol, price, margin)) return false;
   return (margin <= AccountInfoDouble(ACCOUNT_MARGIN_FREE) * 0.5);
}

//+------------------------------------------------------------------+
//| Posizioni e ordini dell'EA                                       |
//+------------------------------------------------------------------+
bool HasOpenPosition()
{
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      if(PositionGetTicket(k) == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic) return true;
   }
   return false;
}

bool HasPendingOrder()
{
   for(int k = OrdersTotal() - 1; k >= 0; k--)
   {
      ulong t = OrderGetTicket(k);
      if(t == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) == _Symbol &&
         (ulong)OrderGetInteger(ORDER_MAGIC) == InpMagic) return true;
   }
   return false;
}

//--- countAsNoRetest: conta l'ordine come "nessun retest avvenuto"
void DeleteOurPendings(bool countAsNoRetest)
{
   for(int k = OrdersTotal() - 1; k >= 0; k--)
   {
      ulong t = OrderGetTicket(k);
      if(t == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) == _Symbol &&
         (ulong)OrderGetInteger(ORDER_MAGIC) == InpMagic)
      {
         if(trade.OrderDelete(t) && countAsNoRetest) g_noRetest++;
      }
   }
}

void CloseOurPositions()
{
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      ulong t = PositionGetTicket(k);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
         if(!trade.PositionClose(t))
            PrintFormat("ATTENZIONE: chiusura fallita (%s)", trade.ResultRetcodeDescription());
   }
}

//+------------------------------------------------------------------+
//| Stato di rischio                                                 |
//+------------------------------------------------------------------+
void UpdateRiskState()
{
   double   equity = AccountInfoDouble(ACCOUNT_EQUITY);
   datetime now    = TimeCurrent();
   datetime day    = now - (now % 86400);
   if(day != g_currentDay) { g_currentDay = day; g_dayStartEquity = equity; }

   double peak = GetPeak();
   if(equity > peak) { SetPeak(equity); peak = equity; }

   if(!IsHalted() && peak > 0.0 && equity <= peak * (1.0 - InpMaxDrawdownPct / 100.0))
   {
      SetHalted();
      PrintFormat("STOP DI EMERGENZA: drawdown oltre il %.1f%% (picco %.2f, equity %.2f). Chiudo e mi fermo.",
                  InpMaxDrawdownPct, peak, equity);
      DeleteOurPendings(false);
      CloseOurPositions();
   }
}

bool DailyLimitHit()
{
   if(g_dayStartEquity <= 0.0) return false;
   return (AccountInfoDouble(ACCOUNT_EQUITY) <= g_dayStartEquity * (1.0 - InpMaxDailyLossPct / 100.0));
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
//| Registro CSV e statistiche per direzione e per anno              |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
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
   if(!IsOurDeal(deal)) return;

   long   dType  = HistoryDealGetInteger(deal, DEAL_TYPE);
   long   dEntry = HistoryDealGetInteger(deal, DEAL_ENTRY);
   double comm   = HistoryDealGetDouble(deal, DEAL_COMMISSION);
   double pnl    = HistoryDealGetDouble(deal, DEAL_PROFIT) + HistoryDealGetDouble(deal, DEAL_SWAP) + comm;
   g_commissionSum += comm;

   // Direzione della POSIZIONE: un'entrata BUY apre un acquisto,
   // un'uscita SELL chiude un acquisto.
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
         g_extraCost += MathAbs(sc);   // stima di uno spread in piu' per operazione
   }

   if(InpLogToCSV) WriteDealToCSV(deal);
}

bool IsOurDeal(ulong deal)
{
   if((ulong)HistoryDealGetInteger(deal, DEAL_MAGIC) == InpMagic) return true;
   long posId = HistoryDealGetInteger(deal, DEAL_POSITION_ID);
   if(posId <= 0) return false;
   if(!HistorySelectByPosition(posId)) return false;
   int n = HistoryDealsTotal();
   for(int k = 0; k < n; k++)
   {
      ulong d = HistoryDealGetTicket(k);
      if(d > 0 && (ulong)HistoryDealGetInteger(d, DEAL_MAGIC) == InpMagic) return true;
   }
   return false;
}

void WriteDealToCSV(ulong deal)
{
   int h = FileOpen(g_logFile,
                    FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON | FILE_SHARE_READ, ',');
   if(h == INVALID_HANDLE)
   {
      PrintFormat("ATTENZIONE: impossibile aprire il registro %s (errore %d)", g_logFile, GetLastError());
      return;
   }
   if(FileSize(h) == 0)
      FileWrite(h, "mode", "ea_version", "deal_ticket", "position_id", "server_time",
                "server_gmt_offset_sec", "symbol", "deal_type", "entry", "reason",
                "volume", "price", "profit", "commission", "swap",
                "spread_points_at_log", "balance_after");
   FileSeek(h, 0, SEEK_END);

   long   dType   = HistoryDealGetInteger(deal, DEAL_TYPE);
   long   dEntry  = HistoryDealGetInteger(deal, DEAL_ENTRY);
   long   dReason = HistoryDealGetInteger(deal, DEAL_REASON);
   string typeStr  = (dType == DEAL_TYPE_BUY) ? "BUY" : (dType == DEAL_TYPE_SELL ? "SELL" : "OTHER");
   string entryStr = (dEntry == DEAL_ENTRY_IN) ? "IN" : (dEntry == DEAL_ENTRY_OUT ? "OUT" : "OTHER");
   string offset   = g_isTester ? "" : IntegerToString((long)(TimeTradeServer() - TimeGMT()));

   MqlTick tick;
   double spreadPts = -1.0;
   if(SymbolInfoTick(_Symbol, tick) && _Point > 0.0) spreadPts = (tick.ask - tick.bid) / _Point;

   FileWrite(h,
             ModeString(), EA_VERSION,
             IntegerToString((long)deal),
             IntegerToString(HistoryDealGetInteger(deal, DEAL_POSITION_ID)),
             TimeToString((datetime)HistoryDealGetInteger(deal, DEAL_TIME), TIME_DATE | TIME_SECONDS),
             offset, _Symbol, typeStr, entryStr,
             EnumToString((ENUM_DEAL_REASON)dReason),
             DoubleToString(HistoryDealGetDouble(deal, DEAL_VOLUME), 2),
             DoubleToString(HistoryDealGetDouble(deal, DEAL_PRICE), _Digits),
             DoubleToString(HistoryDealGetDouble(deal, DEAL_PROFIT), 2),
             DoubleToString(HistoryDealGetDouble(deal, DEAL_COMMISSION), 2),
             DoubleToString(HistoryDealGetDouble(deal, DEAL_SWAP), 2),
             DoubleToString(spreadPts, 1),
             DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2));
   FileClose(h);
}

//+------------------------------------------------------------------+
//| Utilita'                                                         |
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
   string state = "attivo";
   if(IsHalted())           state = "FERMO - stop di emergenza (sblocco manuale)";
   else if(DailyLimitHit()) state = "in pausa fino a domani (limite giornaliero)";
   Comment(StringFormat("Nucleus EA %s  |  %s  |  %s\nStato: %s\nLivelli di oggi: massimo %s  minimo %s\nEquity: %.2f   Picco: %.2f",
                        EA_VERSION, ModeString(), _Symbol, state,
                        DoubleToString(g_zoneHigh, _Digits), DoubleToString(g_zoneLow, _Digits),
                        AccountInfoDouble(ACCOUNT_EQUITY), GetPeak()));
}
//+------------------------------------------------------------------+
