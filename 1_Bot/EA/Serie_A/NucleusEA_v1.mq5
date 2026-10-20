//+------------------------------------------------------------------+
//|                                              NucleusEA_v1.mq5    |
//|                                              Progetto Nucleus    |
//+------------------------------------------------------------------+
//
// SCOPO
//   EA di test, prudente e trasparente, da usare SOLO su conto DEMO.
//   Non e' costruito per "fare soldi": e' una base pulita e sicura
//   per imparare, misurare costi reali e produrre dati per Nucleus.
//
// STRATEGIA (volutamente semplice, poche regole = meno illusioni)
//   - Segnali calcolati SOLO su candele gia' chiuse (niente "sbirciate").
//   - Acquisto: la EMA veloce incrocia al rialzo la EMA lenta
//               e il prezzo e' sopra la EMA di tendenza (200).
//   - Vendita:  incrocio al ribasso e prezzo sotto la EMA 200.
//   - Stop loss e take profit calcolati con l'ATR (volatilita').
//   - Una sola posizione alla volta. Niente martingala, niente griglie,
//     niente medie di prezzo: se sbaglia, perde solo il rischio fissato.
//
// PROTEZIONI
//   - Limiti rigidi scritti nel codice (#define): gli input non possono
//     superarli. Nucleus o gli agenti non potranno mai alzarli.
//   - Rischio per operazione calcolato sul saldo, arrotondato SEMPRE
//     per difetto. Se il volume minimo supera il rischio: niente trade.
//   - Limite di perdita giornaliera: stop ai nuovi trade fino a domani.
//   - Stop di emergenza sul drawdown: chiude le posizioni dell'EA e si
//     ferma finche' non lo sblocchi TU a mano (vedi in fondo).
//   - Rifiuta di partire su un conto REALE, salvo consenso esplicito.
//   - Filtri su spread, orari, venerdi' sera, margine disponibile.
//
// CRITERI DI VALUTAZIONE (scritti PRIMA del test, da non cambiare dopo)
//   1. Almeno 100 operazioni chiuse prima di qualsiasi giudizio.
//   2. Backtest positivo anche con costi raddoppiati
//      (spread fisso doppio nello Strategy Tester).
//   3. Drawdown massimo del backtest inferiore al 10%.
//   4. Dati 2023-oggi tenuti "in cassaforte": usati UNA sola volta,
//      alla fine, per confermare. Mai per scegliere i parametri.
//   5. Almeno 3 mesi di demo con risultati coerenti col backtest.
//   Se anche un solo criterio fallisce, l'EA e' bocciato.
//
// REGISTRO PER NUCLEUS
//   Ogni operazione viene scritta in un file CSV nella cartella comune
//   di MetaTrader (Common/Files), separato per modalita':
//   Nucleus_EA_TESTER.csv, Nucleus_EA_DEMO.csv
//
// SBLOCCO DELLO STOP DI EMERGENZA
//   In MT5: Strumenti > Variabili globali (F3), elimina la variabile
//   NUCLEUS_EA_<magic>_HALT. Fallo solo dopo aver capito la causa.
//+------------------------------------------------------------------+
#property copyright "Progetto Nucleus"
#property version   "1.00"
#property description "EA prudente di trend-following, solo per conto DEMO."
#property description "Registra ogni operazione in CSV per Nucleus."

#include <Trade\Trade.mqh>

//--- LIMITI RIGIDI: non modificabili dagli input -------------------
#define HARD_MAX_RISK_PCT        1.0    // rischio massimo per operazione
#define HARD_MAX_DAILY_LOSS_PCT  3.0    // perdita massima giornaliera
#define HARD_MAX_DRAWDOWN_PCT   15.0    // drawdown massimo prima dello stop
#define EA_VERSION              "1.00"

//--- INPUT -----------------------------------------------------------
input group "Strategia"
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_H1; // Timeframe dei segnali
input int    InpFastEMA   = 20;     // EMA veloce
input int    InpSlowEMA   = 50;     // EMA lenta
input int    InpTrendEMA  = 200;    // EMA di tendenza (filtro)
input int    InpATRPeriod = 14;     // Periodo ATR
input double InpSL_ATR    = 2.0;    // Stop loss = ATR x questo valore
input double InpTP_ATR    = 3.0;    // Take profit = ATR x questo valore

input group "Rischio"
input double InpRiskPct         = 0.5;  // Rischio per operazione (% saldo, max 1.0)
input double InpMaxDailyLossPct = 2.0;  // Perdita giornaliera massima (% , max 3.0)
input double InpMaxDrawdownPct  = 10.0; // Drawdown per stop di emergenza (%, max 15)
input double InpMaxLots         = 1.0;  // Volume massimo assoluto (lotti)

input group "Filtri di esecuzione"
input int  InpMaxSpreadPoints   = 20;   // Spread massimo in punti (20 = 2 pip su EURUSD)
input int  InpMaxSlippagePoints = 10;   // Slippage massimo accettato (punti)
input int  InpStartHour         = 7;    // Ora di inizio (ora del server)
input int  InpEndHour           = 20;   // Ora di fine (ora del server)
input int  InpFridayLastHour    = 16;   // Venerdi': nessun nuovo trade da quest'ora
input bool InpCloseBeforeWeekend = true; // Venerdi': chiudi le posizioni prima del weekend
input int  InpFridayCloseHour   = 20;   // Venerdi': ora di chiusura posizioni

input group "Sicurezza e registro"
input bool   InpAllowRealAccount = false;       // Consenti conto REALE (lasciare false)
input ulong  InpMagic            = 20260924;    // Numero identificativo dell'EA
input bool   InpLogToCSV         = true;        // Scrivi il registro CSV
input string InpLogPrefix        = "Nucleus_EA";// Prefisso del file di registro

//--- VARIABILI GLOBALI -----------------------------------------------
CTrade   trade;
int      hFast  = INVALID_HANDLE;
int      hSlow  = INVALID_HANDLE;
int      hTrend = INVALID_HANDLE;
int      hATR   = INVALID_HANDLE;

bool     g_isTester       = false;
datetime g_lastBarTime    = 0;
datetime g_currentDay     = 0;
double   g_dayStartEquity = 0.0;
double   g_peakMem        = 0.0;   // usato solo nello Strategy Tester
bool     g_haltMem        = false; // usato solo nello Strategy Tester
string   g_gvPeak         = "";
string   g_gvHalt         = "";
string   g_logFile        = "";

//+------------------------------------------------------------------+
//| Avvio                                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   g_isTester = (bool)MQLInfoInteger(MQL_TESTER);

   //--- 1. Controllo dei parametri contro i limiti rigidi
   if(InpRiskPct <= 0.0 || InpRiskPct > HARD_MAX_RISK_PCT)
   { Print("ERRORE: rischio per operazione fuori dai limiti (0 - ", HARD_MAX_RISK_PCT, "%)."); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxDailyLossPct <= 0.0 || InpMaxDailyLossPct > HARD_MAX_DAILY_LOSS_PCT)
   { Print("ERRORE: perdita giornaliera fuori dai limiti (0 - ", HARD_MAX_DAILY_LOSS_PCT, "%)."); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxDrawdownPct <= 0.0 || InpMaxDrawdownPct > HARD_MAX_DRAWDOWN_PCT)
   { Print("ERRORE: drawdown massimo fuori dai limiti (0 - ", HARD_MAX_DRAWDOWN_PCT, "%)."); return INIT_PARAMETERS_INCORRECT; }
   if(!(InpFastEMA > 0 && InpFastEMA < InpSlowEMA && InpSlowEMA < InpTrendEMA))
   { Print("ERRORE: deve valere EMA veloce < EMA lenta < EMA di tendenza."); return INIT_PARAMETERS_INCORRECT; }
   if(InpATRPeriod <= 0 || InpSL_ATR <= 0.0 || InpTP_ATR <= 0.0)
   { Print("ERRORE: parametri ATR non validi."); return INIT_PARAMETERS_INCORRECT; }
   if(InpStartHour < 0 || InpEndHour > 24 || InpStartHour >= InpEndHour)
   { Print("ERRORE: orari di trading non validi."); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxLots <= 0.0 || InpMaxSpreadPoints <= 0 || InpMaxSlippagePoints < 0)
   { Print("ERRORE: filtri di esecuzione non validi."); return INIT_PARAMETERS_INCORRECT; }

   //--- 2. Blocco del conto reale
   ENUM_ACCOUNT_TRADE_MODE accMode = (ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE);
   if(!g_isTester && accMode == ACCOUNT_TRADE_MODE_REAL && !InpAllowRealAccount)
   {
      Print("BLOCCO DI SICUREZZA: questo e' un conto REALE. L'EA non parte.");
      return INIT_FAILED;
   }

   //--- 3. Indicatori
   hFast  = iMA(_Symbol, InpTimeframe, InpFastEMA,  0, MODE_EMA, PRICE_CLOSE);
   hSlow  = iMA(_Symbol, InpTimeframe, InpSlowEMA,  0, MODE_EMA, PRICE_CLOSE);
   hTrend = iMA(_Symbol, InpTimeframe, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   hATR   = iATR(_Symbol, InpTimeframe, InpATRPeriod);
   if(hFast == INVALID_HANDLE || hSlow == INVALID_HANDLE ||
      hTrend == INVALID_HANDLE || hATR == INVALID_HANDLE)
   {
      Print("ERRORE: impossibile creare gli indicatori.");
      return INIT_FAILED;
   }

   //--- 4. Esecuzione ordini
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpMaxSlippagePoints);
   trade.SetTypeFillingBySymbol(_Symbol);

   //--- 5. Stato di rischio persistente
   g_gvPeak = "NUCLEUS_EA_" + IntegerToString((long)InpMagic) + "_PEAK";
   g_gvHalt = "NUCLEUS_EA_" + IntegerToString((long)InpMagic) + "_HALT";
   if(GetPeak() <= 0.0)
      SetPeak(AccountInfoDouble(ACCOUNT_EQUITY));

   //--- 6. Registro
   g_logFile = InpLogPrefix + "_" + ModeString() + ".csv";

   //--- 7. Il primo segnale viene valutato alla PROSSIMA candela,
   //       cosi' non si entra in ritardo su un incrocio gia' vecchio.
   g_lastBarTime = iTime(_Symbol, InpTimeframe, 0);

   PrintFormat("Nucleus EA v%s avviato su %s | modalita' %s | rischio %.2f%% | registro %s",
               EA_VERSION, _Symbol, ModeString(), InpRiskPct, g_logFile);
   if(IsHalted())
      Print("ATTENZIONE: stop di emergenza ATTIVO. Nessun nuovo trade finche' non viene sbloccato.");

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Chiusura                                                         |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(hFast  != INVALID_HANDLE) IndicatorRelease(hFast);
   if(hSlow  != INVALID_HANDLE) IndicatorRelease(hSlow);
   if(hTrend != INVALID_HANDLE) IndicatorRelease(hTrend);
   if(hATR   != INVALID_HANDLE) IndicatorRelease(hATR);
   Comment("");
}

//+------------------------------------------------------------------+
//| Ciclo principale                                                 |
//+------------------------------------------------------------------+
void OnTick()
{
   UpdateRiskState();
   if(!g_isTester) ShowStatus();

   if(IsHalted()) return;

   //--- Chiusura prima del weekend (i gap del lunedi' possono saltare lo stop)
   if(InpCloseBeforeWeekend && IsFridayCloseTime() && HasOpenPosition())
   {
      Print("Venerdi' sera: chiudo le posizioni prima del weekend.");
      CloseOurPositions();
      return;
   }

   if(!IsNewBar())          return; // una sola valutazione per candela
   if(DailyLimitHit())      return;
   if(HasOpenPosition())    return;
   if(!TradingAllowedNow()) return;
   if(!SpreadOK())          return; // se lo spread e' alto, si salta la candela

   int signal = GetSignal();
   if(signal != 0)
      OpenTrade(signal);
}

//+------------------------------------------------------------------+
//| Stato di rischio: giorno, picco, stop di emergenza               |
//+------------------------------------------------------------------+
void UpdateRiskState()
{
   double   equity = AccountInfoDouble(ACCOUNT_EQUITY);
   datetime now    = TimeCurrent();
   datetime day    = now - (now % 86400);

   // Nota: se l'EA viene riavviato durante il giorno, il riferimento
   // giornaliero riparte dal valore attuale (scelta prudente e semplice).
   if(day != g_currentDay)
   {
      g_currentDay     = day;
      g_dayStartEquity = equity;
   }

   double peak = GetPeak();
   if(equity > peak)
   {
      SetPeak(equity);
      peak = equity;
   }

   if(!IsHalted() && peak > 0.0 && equity <= peak * (1.0 - InpMaxDrawdownPct / 100.0))
   {
      SetHalted();
      PrintFormat("STOP DI EMERGENZA: drawdown oltre il %.1f%% (picco %.2f, equity %.2f). Chiudo e mi fermo.",
                  InpMaxDrawdownPct, peak, equity);
      CloseOurPositions();
   }
}

bool DailyLimitHit()
{
   if(g_dayStartEquity <= 0.0) return false;
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   return (equity <= g_dayStartEquity * (1.0 - InpMaxDailyLossPct / 100.0));
}

//--- Nel tester lo stato vive in memoria, sul conto demo in variabili
//--- globali del terminale (sopravvive ai riavvii di MT5).
double GetPeak()
{
   if(g_isTester) return g_peakMem;
   return GlobalVariableCheck(g_gvPeak) ? GlobalVariableGet(g_gvPeak) : 0.0;
}
void SetPeak(double value)
{
   if(g_isTester) g_peakMem = value;
   else GlobalVariableSet(g_gvPeak, value);
}
bool IsHalted()
{
   if(g_isTester) return g_haltMem;
   return (GlobalVariableCheck(g_gvHalt) && GlobalVariableGet(g_gvHalt) > 0.5);
}
void SetHalted()
{
   if(g_isTester) g_haltMem = true;
   else GlobalVariableSet(g_gvHalt, 1.0);
}

//+------------------------------------------------------------------+
//| Filtri                                                           |
//+------------------------------------------------------------------+
bool IsNewBar()
{
   datetime t = iTime(_Symbol, InpTimeframe, 0);
   if(t == 0 || t == g_lastBarTime) return false;
   g_lastBarTime = t;
   return true;
}

bool TradingAllowedNow()
{
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED))
      return false;
   if(SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE) != SYMBOL_TRADE_MODE_FULL)
      return false;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(dt.day_of_week == 0 || dt.day_of_week == 6) return false;
   if(dt.hour < InpStartHour || dt.hour >= InpEndHour) return false;
   if(dt.day_of_week == 5 && dt.hour >= InpFridayLastHour) return false;
   return true;
}

bool IsFridayCloseTime()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   return (dt.day_of_week == 5 && dt.hour >= InpFridayCloseHour);
}

double CurrentSpreadPoints()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick) || _Point <= 0.0) return -1.0;
   return (tick.ask - tick.bid) / _Point;
}

bool SpreadOK()
{
   double spread = CurrentSpreadPoints();
   return (spread >= 0.0 && spread <= InpMaxSpreadPoints);
}

bool HasOpenPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
         return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Segnale: +1 acquisto, -1 vendita, 0 nessuno                      |
//| Usa solo le candele chiuse 1 (ultima) e 2 (precedente).          |
//+------------------------------------------------------------------+
int GetSignal()
{
   double fast[], slow[], trend[];
   ArraySetAsSeries(fast, true);
   ArraySetAsSeries(slow, true);
   ArraySetAsSeries(trend, true);

   if(CopyBuffer(hFast,  0, 1, 2, fast)  != 2) return 0;
   if(CopyBuffer(hSlow,  0, 1, 2, slow)  != 2) return 0;
   if(CopyBuffer(hTrend, 0, 1, 1, trend) != 1) return 0;

   double close1 = iClose(_Symbol, InpTimeframe, 1);
   if(close1 <= 0.0) return 0;

   // indice 0 = ultima candela chiusa, indice 1 = quella prima
   bool crossUp   = (fast[1] <= slow[1] && fast[0] > slow[0]);
   bool crossDown = (fast[1] >= slow[1] && fast[0] < slow[0]);

   if(crossUp   && close1 > trend[0]) return  1;
   if(crossDown && close1 < trend[0]) return -1;
   return 0;
}

//+------------------------------------------------------------------+
//| Apertura dell'operazione                                         |
//+------------------------------------------------------------------+
void OpenTrade(int signal)
{
   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(hATR, 0, 1, 1, atr) != 1 || atr[0] <= 0.0) return;

   double slDist  = atr[0] * InpSL_ATR;
   double tpDist  = atr[0] * InpTP_ATR;
   double minDist = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   if(slDist <= minDist || tpDist <= minDist)
   {
      Print("Operazione saltata: stop troppo vicini rispetto al minimo del broker.");
      return;
   }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick)) return;

   double price = (signal > 0) ? tick.ask : tick.bid;
   double sl    = NormalizePrice((signal > 0) ? price - slDist : price + slDist);
   double tp    = NormalizePrice((signal > 0) ? price + tpDist : price - tpDist);

   double vol = CalcVolume(signal, price, sl);
   if(vol <= 0.0) return;
   if(!MarginOK(signal, vol, price)) return;

   bool ok = (signal > 0)
             ? trade.Buy(vol,  _Symbol, price, sl, tp, "NucleusEA v1")
             : trade.Sell(vol, _Symbol, price, sl, tp, "NucleusEA v1");

   uint rc = trade.ResultRetcode();
   if(!ok || (rc != TRADE_RETCODE_DONE && rc != TRADE_RETCODE_PLACED))
      PrintFormat("Ordine NON eseguito: codice %u (%s)", rc, trade.ResultRetcodeDescription());
   else
      PrintFormat("Aperta %s %.2f lotti a %.5f | SL %.5f | TP %.5f",
                  (signal > 0 ? "BUY" : "SELL"), vol, trade.ResultPrice(), sl, tp);
}

double NormalizePrice(double p)
{
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(ts > 0.0) p = MathRound(p / ts) * ts;
   return NormalizeDouble(p, _Digits);
}

//--- Volume in base al rischio: arrotondato SEMPRE per difetto
double CalcVolume(int signal, double price, double sl)
{
   double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPct / 100.0;
   ENUM_ORDER_TYPE type = (signal > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;

   double pnl = 0.0;
   if(!OrderCalcProfit(type, _Symbol, 1.0, price, sl, pnl)) return 0.0;
   double lossPerLot = MathAbs(pnl);
   if(lossPerLot <= 0.0) return 0.0;

   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(step <= 0.0) return 0.0;

   double vol = riskMoney / lossPerLot;
   vol = MathMin(vol, MathMin(vmax, InpMaxLots));
   vol = MathFloor(vol / step + 1e-9) * step;

   if(vol < vmin)
   {
      PrintFormat("Operazione saltata: il volume minimo (%.2f) supererebbe il rischio consentito.", vmin);
      return 0.0;
   }
   int vdigits = (int)MathMax(0, MathRound(-MathLog10(step)));
   return NormalizeDouble(vol, vdigits);
}

//--- Non usare mai piu' della meta' del margine libero
bool MarginOK(int signal, double vol, double price)
{
   ENUM_ORDER_TYPE type = (signal > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double margin = 0.0;
   if(!OrderCalcMargin(type, _Symbol, vol, price, margin)) return false;
   if(margin > AccountInfoDouble(ACCOUNT_MARGIN_FREE) * 0.5)
   {
      Print("Operazione saltata: margine richiesto troppo alto.");
      return false;
   }
   return true;
}

void CloseOurPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
      {
         if(!trade.PositionClose(ticket))
            PrintFormat("ATTENZIONE: chiusura fallita per la posizione %I64u (%s)",
                        ticket, trade.ResultRetcodeDescription());
      }
   }
}

//+------------------------------------------------------------------+
//| Registro CSV per Nucleus                                         |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
   if(!InpLogToCSV) return;
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

   WriteDealToCSV(deal);
}

//--- Le chiusure da SL/TP vengono riconosciute tramite la posizione
bool IsOurDeal(ulong deal)
{
   if((ulong)HistoryDealGetInteger(deal, DEAL_MAGIC) == InpMagic) return true;

   long posId = HistoryDealGetInteger(deal, DEAL_POSITION_ID);
   if(posId <= 0) return false;
   if(!HistorySelectByPosition(posId)) return false;

   int n = HistoryDealsTotal();
   for(int i = 0; i < n; i++)
   {
      ulong d = HistoryDealGetTicket(i);
      if(d > 0 && (ulong)HistoryDealGetInteger(d, DEAL_MAGIC) == InpMagic)
         return true;
   }
   return false;
}

void WriteDealToCSV(ulong deal)
{
   int h = FileOpen(g_logFile,
                    FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON | FILE_SHARE_READ,
                    ',');
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

   FileWrite(h,
             ModeString(),
             EA_VERSION,
             IntegerToString((long)deal),
             IntegerToString(HistoryDealGetInteger(deal, DEAL_POSITION_ID)),
             TimeToString((datetime)HistoryDealGetInteger(deal, DEAL_TIME), TIME_DATE | TIME_SECONDS),
             offset,
             _Symbol,
             typeStr,
             entryStr,
             EnumToString((ENUM_DEAL_REASON)dReason),
             DoubleToString(HistoryDealGetDouble(deal, DEAL_VOLUME), 2),
             DoubleToString(HistoryDealGetDouble(deal, DEAL_PRICE), _Digits),
             DoubleToString(HistoryDealGetDouble(deal, DEAL_PROFIT), 2),
             DoubleToString(HistoryDealGetDouble(deal, DEAL_COMMISSION), 2),
             DoubleToString(HistoryDealGetDouble(deal, DEAL_SWAP), 2),
             DoubleToString(CurrentSpreadPoints(), 1),
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

   Comment(StringFormat("Nucleus EA v%s  |  %s  |  %s\nStato: %s\nEquity: %.2f   Picco: %.2f\nRischio: %.2f%%   Limite giorno: %.1f%%   Drawdown max: %.1f%%",
                        EA_VERSION, ModeString(), _Symbol, state,
                        AccountInfoDouble(ACCOUNT_EQUITY), GetPeak(),
                        InpRiskPct, InpMaxDailyLossPct, InpMaxDrawdownPct));
}
//+------------------------------------------------------------------+
