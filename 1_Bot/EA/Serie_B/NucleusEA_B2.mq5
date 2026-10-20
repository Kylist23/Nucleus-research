//+------------------------------------------------------------------+
//|                                                NucleusEA_B2.mq5  |
//|                                                Progetto Nucleus  |
//+------------------------------------------------------------------+
//
// SERIE B, TENTATIVO 2 (idee provate in totale: 5)
//   Serie A (tendenza) chiusa dopo 3 tentativi bocciati.
//   B1 (rottura e retest dei livelli del giorno prima) bocciato il
//   2026-10-09: stop di emergenza nel 2018, entrambe le direzioni in perdita.
//
// IDEA: EFFETTO "NOTTE E GIORNO" DELL'ORO
//   Diverse analisi hanno osservato che gran parte del rialzo dell'oro
//   avviene nelle ore asiatiche, mentre nelle ore di Londra e New York
//   l'andamento medio e' piatto o in calo. Nessun indicatore: solo orari.
//
// REGOLE (orari del server, fissati PRIMA del test, mai ottimizzati)
//   Si assume un server GMT+2 / GMT+3 con l'ora legale USA, come quasi
//   tutti i broker MT5: mezzanotte del server = chiusura di New York.
//   - NOTTE: acquisto alle 01:00, chiusura alle 10:00 (apertura di Londra).
//   - GIORNO: vendita alle 10:00, chiusura alle 22:00 (prima della chiusura
//     giornaliera, quindi niente swap).
//
// VERSIONE 1.01 (correzione di esecuzione, NON della regola)
//   Nella 1.00 la chiusura era alle 23:00, ma il broker non esegue ordini
//   sull'oro dalle 23:00 all'01:00 (i prezzi arrivano, gli ordini no):
//   le vendite restavano aperte fino all'01:00
//   del giorno dopo, pagando swap e spread notturno. La regola voleva
//   "chiudere prima della chiusura giornaliera": ora si chiude alle 22:00,
//   e in ogni caso una posizione non supera mai il cambio di giorno.
//   - Stop di protezione: 1 x ATR(14) giornaliero. Nessun target: si esce
//     all'orario. Lo stop serve a limitare i disastri e a calcolare il lotto.
//   - Una posizione alla volta. Il venerdi' si chiude alle 20:00.
//
// CRITERI DI VALUTAZIONE (registrati nel manuale PRIMA del test)
//   XAUUSD, 2016.01.01 - 2022.12.31. Cassaforte 2023-oggi intatta.
//   1. Almeno 100 operazioni.
//   2. Risultato dell'OnTester (costi raddoppiati) maggiore di zero.
//   3. Profitto netto positivo sia sugli acquisti (notte) sia sulle
//      vendite (giorno).
//   4. Profitto netto positivo sia nel 2016-2019 sia nel 2020-2022.
//   5. Drawdown relativo dell'equity sotto il 10%.
//   Il confronto con il buy-and-hold dell'oro viene riportato, ma non e'
//   un criterio.
//
// SBLOCCO DELLO STOP DI EMERGENZA (solo su conto demo)
//   Strumenti > Variabili globali (F3): elimina NUCLEUS_EA_<magic>_HALT.
//+------------------------------------------------------------------+
#property copyright "Progetto Nucleus"
#property version   "1.01"
#property description "Serie B2: effetto notte e giorno dell'oro. Solo DEMO."

#include <Trade\Trade.mqh>

//--- LIMITI RIGIDI --------------------------------------------------
#define HARD_MAX_RISK_PCT        1.0
#define HARD_MAX_DAILY_LOSS_PCT  3.0
#define HARD_MAX_DRAWDOWN_PCT   15.0
#define EA_VERSION              "B2-1.01"
#define FIRST_YEAR               2000
#define MAX_YEARS                60

// Orari fissi nel codice (non modificabili dal tester, che ricorda i
// valori dei test precedenti): fissati prima del test, non si ottimizzano.
#define InpNightOpenHour   1    // NOTTE: ora di acquisto (server)
#define InpNightCloseHour 10    // NOTTE: ora di chiusura (server)
#define InpDayOpenHour    10    // GIORNO: ora di vendita (server)
#define InpDayCloseHour   22    // GIORNO: ora di chiusura (server)

//--- INPUT -----------------------------------------------------------
input group "Strategia (orari fissati prima del test, non ottimizzare)"
input int    InpATRPeriod      = 14;   // Periodo ATR (D1)
input double InpSL_ATR         = 1.0;  // Stop di protezione = ATR giornaliero x questo valore

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
input ulong  InpMagic            = 20261009;       // Numero identificativo dell'EA
input bool   InpLogToCSV         = true;           // Scrivi il registro CSV
input string InpLogName          = "Nucleus_EAB2v101"; // Prefisso del file di registro

//--- VARIABILI GLOBALI -----------------------------------------------
CTrade   trade;
int      hATR = INVALID_HANDLE;

bool     g_isTester = false;
datetime g_legDay = 0;
bool     g_nightDone = false, g_dayDone = false;
int      g_openLeg = 0;                 // 1 = notte (acquisto), -1 = giorno (vendita), 0 = nessuna
datetime g_openDay = 0;                 // giorno di apertura della posizione

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
int      g_skipSpread = 0, g_skipOther = 0, g_skipDaily = 0, g_stopHits = 0;

//+------------------------------------------------------------------+
//| Avvio                                                            |
//+------------------------------------------------------------------+
bool HourOK(int h) { return (h >= 0 && h <= 23); }

int OnInit()
{
   g_isTester = (bool)MQLInfoInteger(MQL_TESTER);

   if(InpRiskPct <= 0.0 || InpRiskPct > HARD_MAX_RISK_PCT)
   { Print("ERRORE: rischio per operazione fuori dai limiti."); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxDailyLossPct <= 0.0 || InpMaxDailyLossPct > HARD_MAX_DAILY_LOSS_PCT)
   { Print("ERRORE: perdita giornaliera fuori dai limiti."); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxDrawdownPct <= 0.0 || InpMaxDrawdownPct > HARD_MAX_DRAWDOWN_PCT)
   { Print("ERRORE: drawdown massimo fuori dai limiti."); return INIT_PARAMETERS_INCORRECT; }
   if(InpSL_ATR <= 0.0 || InpATRPeriod <= 0)
   { Print("ERRORE: parametri della strategia non validi."); return INIT_PARAMETERS_INCORRECT; }
   if(!HourOK(InpNightOpenHour) || !HourOK(InpNightCloseHour) || !HourOK(InpDayOpenHour) || !HourOK(InpDayCloseHour) ||
      !(InpNightOpenHour < InpNightCloseHour && InpNightCloseHour <= InpDayOpenHour && InpDayOpenHour < InpDayCloseHour))
   { Print("ERRORE: orari non validi (serve notte < giorno, nello stesso giorno)."); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxLots <= 0.0 || InpMaxSpreadPctOfSL <= 0.0 || InpMaxSpreadPctOfSL > 25.0)
   { Print("ERRORE: volume massimo o filtro spread non validi."); return INIT_PARAMETERS_INCORRECT; }

   ENUM_ACCOUNT_TRADE_MODE accMode = (ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE);
   if(!g_isTester && accMode == ACCOUNT_TRADE_MODE_REAL && !InpAllowRealAccount)
   {
      Print("BLOCCO DI SICUREZZA: questo e' un conto REALE. L'EA non parte.");
      return INIT_FAILED;
   }

   //--- Indicatore creato UNA volta sola
   hATR = iATR(_Symbol, PERIOD_D1, InpATRPeriod);
   if(hATR == INVALID_HANDLE)
   { Print("ERRORE: impossibile creare l'ATR."); return INIT_FAILED; }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);

   g_gvPeak = "NUCLEUS_EA_" + IntegerToString((long)InpMagic) + "_PEAK";
   g_gvHalt = "NUCLEUS_EA_" + IntegerToString((long)InpMagic) + "_HALT";
   if(GetPeak() <= 0.0) SetPeak(AccountInfoDouble(ACCOUNT_EQUITY));

   g_logFile = "Nucleus\\" + InpLogName + "_" + ModeString() + "_" + _Symbol + ".csv";

   g_trades[0] = 0; g_trades[1] = 0; g_net[0] = 0.0; g_net[1] = 0.0;
   ArrayInitialize(g_netYear, 0.0);

   if(!g_isTester)
      PrintFormat("Orario server meno GMT: %d ore. Le regole assumono +2 d'inverno e +3 d'estate.",
                  (int)MathRound((double)(TimeTradeServer() - TimeGMT()) / 3600.0));

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

   PrintFormat("RIEPILOGO B2 %s: entrate tentate %d | stop di protezione colpiti %d | scartati: lotto minimo %d, spread %d, limite giornaliero %d, altro %d",
               _Symbol, g_setups, g_stopHits, g_skipMinVol, g_skipSpread, g_skipDaily, g_skipOther);
   PrintFormat("RIEPILOGO B2 %s: acquisti NOTTE %d (netto %.2f) | vendite GIORNO %d (netto %.2f)",
               _Symbol, g_trades[0], g_net[0], g_trades[1], g_net[1]);

   double bhEnd = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double bhPct = (g_bhStart > 0.0 && bhEnd > 0.0) ? (bhEnd / g_bhStart - 1.0) * 100.0 : 0.0;
   PrintFormat("RIEPILOGO B2 %s: netto %.2f | con costi raddoppiati (stima) %.2f | buy-and-hold nel periodo %.2f%%",
               _Symbol, net, stress, bhPct);

   for(int y = 0; y < MAX_YEARS; y++)
      if(g_netYear[y] != 0.0)
         PrintFormat("RIEPILOGO B2 %s anno %d: netto %.2f", _Symbol, FIRST_YEAR + y, g_netYear[y]);

   if(hATR != INVALID_HANDLE) IndicatorRelease(hATR);
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
   if(IsHalted()) return;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   bool open = HasOpenPosition();
   if(!open) g_openLeg = 0;

   //--- Venerdi' sera: si chiude tutto e non si apre nulla
   if(InpCloseBeforeWeekend && dt.day_of_week == 5 && dt.hour >= InpFridayCloseHour)
   {
      if(open) CloseOurPositions();
      return;
   }

   //--- Nuovo giorno: entrambe le fasi di nuovo disponibili
   datetime d0 = TimeCurrent() - (TimeCurrent() % 86400);
   if(d0 != g_legDay) { g_legDay = d0; g_nightDone = false; g_dayDone = false; }

   //--- Uscite all'orario
   if(open)
   {
      bool closeNight = (g_openLeg == 1  && (dt.hour >= InpNightCloseHour || dt.hour < InpNightOpenHour));
      bool closeDay   = (g_openLeg == -1 && (dt.hour >= InpDayCloseHour   || dt.hour < InpDayOpenHour));
      bool unknown    = (g_openLeg == 0);   // posizione ereditata (es. riavvio): si chiude
      bool newDay     = (g_openDay != 0 && g_openDay != d0);   // mai oltre il cambio di giorno
      if(closeNight || closeDay || unknown || newDay) { CloseOurPositions(); return; }
      return;                               // una posizione alla volta
   }

   if(dt.day_of_week < 1 || dt.day_of_week > 5) return;
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED)) return;

   //--- Entrate: solo nell'ora prevista, una volta per giorno e per fase
   if(!g_nightDone && dt.hour == InpNightOpenHour)
   {
      g_nightDone = true; g_setups++;
      if(DailyLimitHit()) { g_skipDaily++; return; }
      OpenLeg(1);
   }
   else if(!g_dayDone && dt.hour == InpDayOpenHour)
   {
      g_dayDone = true; g_setups++;
      if(DailyLimitHit()) { g_skipDaily++; return; }
      OpenLeg(-1);
   }
}

//+------------------------------------------------------------------+
//| Apertura a mercato con stop di protezione                        |
//+------------------------------------------------------------------+
void OpenLeg(int dir)
{
   double atr[];
   if(CopyBuffer(hATR, 0, 1, 1, atr) != 1 || atr[0] <= 0.0) { g_skipOther++; return; }

   double slDist  = atr[0] * InpSL_ATR;
   double minDist = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   if(slDist <= minDist) { g_skipOther++; return; }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick)) { g_skipOther++; return; }

   double spread = tick.ask - tick.bid;
   if(spread < 0.0 || spread > slDist * InpMaxSpreadPctOfSL / 100.0) { g_skipSpread++; return; }

   double entry = (dir > 0) ? tick.ask : tick.bid;
   double sl    = NormalizePrice(dir > 0 ? entry - slDist : entry + slDist);

   double vol = CalcVolume(dir, entry, sl);
   if(vol <= 0.0) return;
   if(!MarginOK(dir, vol, entry)) { g_skipOther++; return; }

   bool ok = (dir > 0)
             ? trade.Buy(vol, _Symbol, 0.0, sl, 0.0, "NucleusEA B2 notte")
             : trade.Sell(vol, _Symbol, 0.0, sl, 0.0, "NucleusEA B2 giorno");
   uint rc = trade.ResultRetcode();
   if(!ok || (rc != TRADE_RETCODE_DONE && rc != TRADE_RETCODE_PLACED))
   {
      PrintFormat("Ordine NON eseguito: codice %u (%s)", rc, trade.ResultRetcodeDescription());
      g_skipOther++;
      return;
   }
   g_openLeg = dir;
   g_openDay = TimeCurrent() - (TimeCurrent() % 86400);
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
   if(dEntry == DEAL_ENTRY_OUT && HistoryDealGetInteger(deal, DEAL_REASON) == DEAL_REASON_SL) g_stopHits++;

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
   string leg = (g_openLeg == 1) ? "acquisto NOTTE aperto" : (g_openLeg == -1 ? "vendita GIORNO aperta" : "nessuna posizione");
   Comment(StringFormat("Nucleus EA %s  |  %s  |  %s\nStato: %s\nPosizione: %s\nEquity: %.2f   Picco: %.2f",
                        EA_VERSION, ModeString(), _Symbol, state, leg,
                        AccountInfoDouble(ACCOUNT_EQUITY), GetPeak()));
}
//+------------------------------------------------------------------+
