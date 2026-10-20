//+------------------------------------------------------------------+
//|                                                NucleusEA_v3.mq5  |
//|                                                Progetto Nucleus  |
//+------------------------------------------------------------------+
//
// REGISTRO DEI TENTATIVI
//   Tentativo 1: v1.1, incrocio EMA su H1, XAUUSD 2018-2022 -> BOCCIATO
//   Tentativo 2: v2, rottura 20 giorni su D1, 5 mercati 2018-2022 -> BOCCIATO
//                (-21 R su 210 operazioni, 1 mercato su 5 in profitto)
//   Tentativo 3: questa versione. E' L'ULTIMO. Se fallisce, ci si ferma.
//
// IDEA (decisa prima del test, non adattata ai risultati precedenti)
//   Replica semplificata del "time series momentum" a 12 mesi
//   (Moskowitz, Ooi, Pedersen, 2012): una volta al mese, per ogni
//   mercato, si compra se negli ultimi 12 mesi il prezzo e' salito e si
//   vende se e' sceso. Le posizioni sono dimensionate in base alla
//   volatilita', cosi' ogni mercato pesa in modo simile.
//
// REGOLE
//   - Mercati: XAUUSD, EURUSD, GBPUSD, USDJPY, AUDUSD, gestiti insieme.
//   - Segnale: chiusura dell'ultimo mese completo contro la chiusura di
//     12 mesi prima (candele mensili gia' chiuse, niente "sbirciate").
//   - Ogni mese la posizione viene chiusa e riaperta: direzione e
//     dimensione tornano aggiornate.
//   - Esecuzione nei primi 7 giorni del mese, tra le 9 e le 20 (server).
//   - Stop di emergenza: 5 x ATR(20) giornaliero, sempre sul server.
//     Il rischio allo stop e' lo 0,5% del saldo per mercato.
//
// CRITERI DI VALUTAZIONE (registrati PRIMA del test anche nella pagina
// di verifica, da non cambiare dopo)
//   Test unico di portafoglio, 2010.01.01 - 2022.12.31.
//   1. Almeno 100 operazioni in totale.
//   2. "Risultato dell'OnTester" (profitto con costi raddoppiati) > 0.
//   3. Profitto netto positivo in almeno 3 mercati su 5 (righe RIEPILOGO).
//   4. Drawdown relativo dell'equity del portafoglio sotto il 10%.
//   5. Profitto netto positivo sia nel 2010-2015 sia nel 2016-2022
//      (calcolato dal file CSV).
//   Un solo criterio fallito = bocciato.
//
// SBLOCCO DELLO STOP DI EMERGENZA (solo su conto demo)
//   Strumenti > Variabili globali (F3): elimina NUCLEUS_EA_<magic>_HALT.
//+------------------------------------------------------------------+
#property copyright "Progetto Nucleus"
#property version   "3.00"
#property description "Momentum a 12 mesi su 5 mercati, ribilanciamento mensile. Solo DEMO."
#property description "Stima dei costi raddoppiati nel 'Risultato dell'OnTester'."

#include <Trade\Trade.mqh>

//--- LIMITI RIGIDI --------------------------------------------------
#define HARD_MAX_RISK_PCT        1.0
#define HARD_MAX_DAILY_LOSS_PCT  3.0
#define HARD_MAX_DRAWDOWN_PCT   15.0
#define HARD_MAX_POSITIONS       5
#define MAX_SYMBOLS              5
#define EA_VERSION              "3.00"

//--- INPUT -----------------------------------------------------------
input group "Strategia (non ottimizzata)"
input string InpSymbols         = "XAUUSD,EURUSD,GBPUSD,USDJPY,AUDUSD"; // Mercati, separati da virgola
input int    InpLookbackMonths  = 12;   // Mesi per misurare la tendenza
input int    InpATRDays         = 20;   // Periodo ATR giornaliero
input double InpStopATR         = 5.0;  // Stop di emergenza = ATR x questo valore
input int    InpMaxEntryDay     = 7;    // Entrate solo fino a questo giorno del mese

input group "Rischio"
input double InpRiskPct           = 0.5;  // Rischio allo stop per mercato (% saldo, max 1.0)
input double InpMaxDailyLossPct   = 2.0;  // Perdita giornaliera massima (%, max 3.0)
input double InpMaxDrawdownPct    = 10.0; // Drawdown per stop di emergenza (%, max 15)
input double InpMaxLots           = 2.0;  // Volume massimo per posizione (lotti)
input int    InpMaxTotalPositions = 5;    // Posizioni massime dell'EA sul conto

input group "Esecuzione"
input int    InpExecStartHour        = 9;    // Ora di inizio esecuzione (ora server)
input int    InpExecEndHour          = 20;   // Ora di fine esecuzione (ora server)
input double InpMaxSpreadPctOfStop   = 10.0; // Spread massimo (% della distanza dello stop)
input double InpMaxSlippagePctOfStop = 5.0;  // Slippage massimo (% della distanza dello stop)

input group "Sicurezza e registro"
input bool   InpAllowRealAccount = false;         // Consenti conto REALE (lasciare false)
input ulong  InpMagic            = 20260926;      // Numero identificativo dell'EA
input bool   InpLogToCSV         = true;          // Scrivi il registro CSV
input string InpLogPrefix        = "Nucleus_EA3"; // Prefisso del file di registro

//--- VARIABILI GLOBALI -----------------------------------------------
CTrade   trade;
int      g_n = 0;
string   g_sym[MAX_SYMBOLS];
int      g_hATR[MAX_SYMBOLS];
bool     g_done[MAX_SYMBOLS];
datetime g_lastCloseTry[MAX_SYMBOLS];

int      g_opened[MAX_SYMBOLS];
int      g_skipMinVol[MAX_SYMBOLS];
int      g_skipData[MAX_SYMBOLS];
int      g_skipExpired[MAX_SYMBOLS];
int      g_skipOther[MAX_SYMBOLS];
double   g_net[MAX_SYMBOLS];     // profitto + swap + commissioni delle operazioni chiuse
double   g_extra[MAX_SYMBOLS];   // costo stimato di uno spread in piu'

bool     g_isTester       = false;
int      g_monthKey       = 0;
datetime g_currentDay     = 0;
double   g_dayStartEquity = 0.0;
double   g_startEquity    = 0.0;
double   g_peakMem        = 0.0;
bool     g_haltMem        = false;
double   g_commissionSum  = 0.0;
string   g_gvPeak         = "";
string   g_gvHalt         = "";
string   g_logFile        = "";

//+------------------------------------------------------------------+
//| Avvio                                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   g_isTester = (bool)MQLInfoInteger(MQL_TESTER);

   //--- 1. Parametri contro i limiti rigidi
   if(InpRiskPct <= 0.0 || InpRiskPct > HARD_MAX_RISK_PCT)
   { Print("ERRORE: rischio per mercato fuori dai limiti."); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxDailyLossPct <= 0.0 || InpMaxDailyLossPct > HARD_MAX_DAILY_LOSS_PCT)
   { Print("ERRORE: perdita giornaliera fuori dai limiti."); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxDrawdownPct <= 0.0 || InpMaxDrawdownPct > HARD_MAX_DRAWDOWN_PCT)
   { Print("ERRORE: drawdown massimo fuori dai limiti."); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxTotalPositions < 1 || InpMaxTotalPositions > HARD_MAX_POSITIONS)
   { Print("ERRORE: numero massimo di posizioni fuori dai limiti."); return INIT_PARAMETERS_INCORRECT; }
   if(InpLookbackMonths < 1 || InpLookbackMonths > 24 || InpATRDays <= 0 || InpStopATR <= 0.0)
   { Print("ERRORE: parametri della strategia non validi."); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxEntryDay < 1 || InpMaxEntryDay > 28 || InpMaxLots <= 0.0)
   { Print("ERRORE: giorno massimo di entrata o volume non validi."); return INIT_PARAMETERS_INCORRECT; }
   if(InpExecStartHour < 0 || InpExecEndHour > 24 || InpExecStartHour >= InpExecEndHour)
   { Print("ERRORE: orari di esecuzione non validi."); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxSpreadPctOfStop <= 0.0 || InpMaxSpreadPctOfStop > 25.0 ||
      InpMaxSlippagePctOfStop < 0.0 || InpMaxSlippagePctOfStop > 25.0)
   { Print("ERRORE: filtri di spread o slippage non validi."); return INIT_PARAMETERS_INCORRECT; }

   //--- 2. Blocco del conto reale
   ENUM_ACCOUNT_TRADE_MODE accMode = (ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE);
   if(!g_isTester && accMode == ACCOUNT_TRADE_MODE_REAL && !InpAllowRealAccount)
   {
      Print("BLOCCO DI SICUREZZA: questo e' un conto REALE. L'EA non parte.");
      return INIT_FAILED;
   }

   //--- 3. Elenco dei mercati
   string parts[];
   int cnt = StringSplit(InpSymbols, ',', parts);
   g_n = 0;
   for(int k = 0; k < cnt; k++)
   {
      string s = parts[k];
      StringTrimLeft(s);
      StringTrimRight(s);
      if(s == "") continue;
      if(g_n >= MAX_SYMBOLS)
      { Print("ERRORE: al massimo ", MAX_SYMBOLS, " mercati."); return INIT_PARAMETERS_INCORRECT; }
      if(!SymbolSelect(s, true) || SymbolInfoDouble(s, SYMBOL_POINT) <= 0.0)
      { Print("ERRORE: il simbolo ", s, " non esiste su questo server. Controlla il nome nel Market Watch."); return INIT_FAILED; }
      g_sym[g_n] = s;
      g_n++;
   }
   if(g_n == 0)
   { Print("ERRORE: nessun mercato indicato."); return INIT_PARAMETERS_INCORRECT; }

   //--- 4. Indicatori e contatori
   for(int i = 0; i < g_n; i++)
   {
      g_hATR[i] = iATR(g_sym[i], PERIOD_D1, InpATRDays);
      if(g_hATR[i] == INVALID_HANDLE)
      { Print("ERRORE: impossibile creare l'ATR per ", g_sym[i]); return INIT_FAILED; }
      g_done[i] = false; g_lastCloseTry[i] = 0;
      g_opened[i] = 0; g_skipMinVol[i] = 0; g_skipData[i] = 0;
      g_skipExpired[i] = 0; g_skipOther[i] = 0;
      g_net[i] = 0.0; g_extra[i] = 0.0;
   }

   //--- 5. Esecuzione e stato di rischio
   trade.SetExpertMagicNumber(InpMagic);
   g_gvPeak = "NUCLEUS_EA_" + IntegerToString((long)InpMagic) + "_PEAK";
   g_gvHalt = "NUCLEUS_EA_" + IntegerToString((long)InpMagic) + "_HALT";
   g_startEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(GetPeak() <= 0.0) SetPeak(g_startEquity);

   g_logFile = InpLogPrefix + "_" + ModeString() + "_PORTAFOGLIO.csv";

   //--- 6. Mese iniziale: se siamo oltre i primi giorni, si aspetta il mese dopo
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   g_monthKey = dt.year * 12 + dt.mon;
   for(int i = 0; i < g_n; i++) g_done[i] = (dt.day > InpMaxEntryDay);

   PrintFormat("Nucleus EA v%s avviato | %d mercati | modalita' %s | rischio %.2f%% per mercato | registro %s",
               EA_VERSION, g_n, ModeString(), InpRiskPct, g_logFile);
   if(IsHalted())
      Print("ATTENZIONE: stop di emergenza ATTIVO. Nessun nuovo trade finche' non viene sbloccato.");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Chiusura e riepilogo                                             |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   double totNet = 0.0, totExtra = 0.0;
   for(int i = 0; i < g_n; i++)
   {
      double net = g_net[i] + FloatingProfit(g_sym[i]);   // include eventuali posizioni ancora aperte
      totNet   += net;
      totExtra += g_extra[i];
      PrintFormat("RIEPILOGO %s: aperte %d | netto %.2f | con costi raddoppiati (stima) %.2f | scartate: lotto minimo %d, dati insufficienti %d, scadute %d, altro %d",
                  g_sym[i], g_opened[i], net, net - g_extra[i],
                  g_skipMinVol[i], g_skipData[i], g_skipExpired[i], g_skipOther[i]);
   }
   PrintFormat("RIEPILOGO PORTAFOGLIO: netto %.2f | con costi raddoppiati (stima) %.2f",
               totNet, totNet - totExtra - MathAbs(g_commissionSum));

   for(int i = 0; i < g_n; i++)
      if(g_hATR[i] != INVALID_HANDLE) IndicatorRelease(g_hATR[i]);
   Comment("");
}

double OnTester()
{
   double extra = 0.0;
   for(int i = 0; i < g_n; i++) extra += g_extra[i];
   return TesterStatistics(STAT_PROFIT) - (extra + MathAbs(g_commissionSum));
}

//+------------------------------------------------------------------+
//| Ciclo principale                                                 |
//+------------------------------------------------------------------+
void OnTick()
{
   UpdateRiskState();
   if(!g_isTester) ShowStatus();
   if(IsHalted()) return;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);

   //--- Nuovo mese: tutti i mercati vanno ribilanciati
   int key = dt.year * 12 + dt.mon;
   if(key != g_monthKey)
   {
      g_monthKey = key;
      for(int i = 0; i < g_n; i++) g_done[i] = false;
   }

   //--- Oltre i primi giorni del mese: chi non e' stato ribilanciato salta il mese
   if(dt.day > InpMaxEntryDay)
   {
      for(int i = 0; i < g_n; i++)
         if(!g_done[i]) { g_skipExpired[i]++; g_done[i] = true; }
      return;
   }

   if(!ExecWindowOK(dt)) return;
   if(DailyLimitHit())   return;

   for(int i = 0; i < g_n; i++)
   {
      if(g_done[i]) continue;
      int r = Rebalance(i);
      if(r != 0) g_done[i] = true;   // 0 = riprova piu' tardi
   }
}

//--- 1 = fatto, 0 = riprova, -1 = saltato per questo mese
int Rebalance(int i)
{
   string s = g_sym[i];
   int sig = MomentumSignal(i);
   if(sig == 2) return 0;                        // dati non ancora pronti
   if(sig == 0)
   {
      g_skipData[i]++;
      if(HasPosition(s)) CloseSymbolPositions(i);
      return -1;
   }

   // La posizione del mese precedente si chiude sempre prima di riaprire.
   if(HasPosition(s))
   {
      CloseSymbolPositions(i);
      if(HasPosition(s)) return 0;
   }
   return OpenTrade(i, sig);
}

//--- +1 comprare, -1 vendere, 0 dati insufficienti, 2 dati non ancora pronti
int MomentumSignal(int i)
{
   string s = g_sym[i];
   int need = InpLookbackMonths + 1;
   if(Bars(s, PERIOD_MN1) < need + 1) return 0;

   double c[];
   if(CopyClose(s, PERIOD_MN1, 1, need, c) != need) return 2;
   // c[0] = chiusura di 12 mesi fa, c[need-1] = chiusura dell'ultimo mese completo
   if(c[0] <= 0.0 || c[need - 1] <= 0.0) return 0;
   double ret = c[need - 1] / c[0] - 1.0;
   if(ret > 0.0) return  1;
   if(ret < 0.0) return -1;
   return 0;
}

//+------------------------------------------------------------------+
//| Apertura: 1 = aperta, 0 = riprova, -1 = saltata                  |
//+------------------------------------------------------------------+
int OpenTrade(int i, int signal)
{
   string s = g_sym[i];

   if(CountOurPositionsAll() >= InpMaxTotalPositions)
   { g_skipOther[i]++; return -1; }
   if(SymbolInfoInteger(s, SYMBOL_TRADE_MODE) != SYMBOL_TRADE_MODE_FULL) return 0;

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR[i], 0, 1, 1, atr) != 1 || atr[0] <= 0.0) return 0;

   double point   = SymbolInfoDouble(s, SYMBOL_POINT);
   int    digits  = (int)SymbolInfoInteger(s, SYMBOL_DIGITS);
   double slDist  = atr[0] * InpStopATR;
   double minDist = (double)SymbolInfoInteger(s, SYMBOL_TRADE_STOPS_LEVEL) * point;
   if(point <= 0.0 || slDist <= minDist)
   { g_skipOther[i]++; return -1; }

   MqlTick tick;
   if(!SymbolInfoTick(s, tick) || tick.ask <= 0.0 || tick.bid <= 0.0) return 0;

   double spread = tick.ask - tick.bid;
   if(spread < 0.0 || spread > slDist * InpMaxSpreadPctOfStop / 100.0) return 0;

   trade.SetTypeFillingBySymbol(s);
   trade.SetDeviationInPoints((ulong)MathMax(1.0, MathFloor(slDist * InpMaxSlippagePctOfStop / 100.0 / point)));

   double price = (signal > 0) ? tick.ask : tick.bid;
   double sl    = NormalizePrice(s, (signal > 0) ? price - slDist : price + slDist, digits);

   double vol = CalcVolume(i, signal, price, sl);
   if(vol <= 0.0) return -1;
   if(!MarginOK(s, signal, vol, price)) { g_skipOther[i]++; return -1; }

   bool ok = (signal > 0)
             ? trade.Buy(vol,  s, price, sl, 0.0, "NucleusEA v3")
             : trade.Sell(vol, s, price, sl, 0.0, "NucleusEA v3");
   uint rc = trade.ResultRetcode();
   if(!ok || (rc != TRADE_RETCODE_DONE && rc != TRADE_RETCODE_PLACED))
   {
      PrintFormat("%s: ordine NON eseguito, codice %u (%s)", s, rc, trade.ResultRetcodeDescription());
      g_skipOther[i]++;
      return -1;
   }

   g_opened[i]++;
   double sc = 0.0;
   if(OrderCalcProfit(ORDER_TYPE_BUY, s, vol, tick.ask, tick.bid, sc))
      g_extra[i] += MathAbs(sc);

   PrintFormat("%s: aperta %s %.2f lotti a %s | stop %s",
               s, (signal > 0 ? "BUY" : "SELL"), vol,
               DoubleToString(trade.ResultPrice(), digits), DoubleToString(sl, digits));
   return 1;
}

double NormalizePrice(string s, double p, int digits)
{
   double ts = SymbolInfoDouble(s, SYMBOL_TRADE_TICK_SIZE);
   if(ts > 0.0) p = MathRound(p / ts) * ts;
   return NormalizeDouble(p, digits);
}

//--- Volume in base al rischio: arrotondato SEMPRE per difetto
double CalcVolume(int i, int signal, double price, double sl)
{
   string s = g_sym[i];
   double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPct / 100.0;
   ENUM_ORDER_TYPE type = (signal > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;

   double pnl = 0.0;
   if(!OrderCalcProfit(type, s, 1.0, price, sl, pnl)) { g_skipOther[i]++; return 0.0; }
   double lossPerLot = MathAbs(pnl);
   if(lossPerLot <= 0.0) { g_skipOther[i]++; return 0.0; }

   double step = SymbolInfoDouble(s, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(s, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(s, SYMBOL_VOLUME_MAX);
   if(step <= 0.0) { g_skipOther[i]++; return 0.0; }

   double vol = riskMoney / lossPerLot;
   vol = MathMin(vol, MathMin(vmax, InpMaxLots));
   vol = MathFloor(vol / step + 1e-9) * step;

   if(vol < vmin)
   {
      PrintFormat("%s: operazione saltata, il volume minimo (%.2f) supererebbe il rischio consentito.", s, vmin);
      g_skipMinVol[i]++;
      return 0.0;
   }
   int vdigits = (int)MathMax(0, MathRound(-MathLog10(step)));
   return NormalizeDouble(vol, vdigits);
}

bool MarginOK(string s, int signal, double vol, double price)
{
   ENUM_ORDER_TYPE type = (signal > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double margin = 0.0;
   if(!OrderCalcMargin(type, s, vol, price, margin)) return false;
   if(margin > AccountInfoDouble(ACCOUNT_MARGIN_FREE) * 0.5)
   {
      PrintFormat("%s: operazione saltata, margine richiesto troppo alto.", s);
      return false;
   }
   return true;
}

//+------------------------------------------------------------------+
//| Posizioni                                                        |
//+------------------------------------------------------------------+
bool HasPosition(string s)
{
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      if(PositionGetTicket(k) == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == s &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic) return true;
   }
   return false;
}

int CountOurPositionsAll()
{
   int n = 0;
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      if(PositionGetTicket(k) == 0) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic) n++;
   }
   return n;
}

double FloatingProfit(string s)
{
   double f = 0.0;
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      if(PositionGetTicket(k) == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == s &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
         f += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
   }
   return f;
}

//--- Chiude le posizioni di un mercato, al massimo un tentativo al minuto
void CloseSymbolPositions(int i)
{
   if(TimeCurrent() - g_lastCloseTry[i] < 60) return;
   g_lastCloseTry[i] = TimeCurrent();
   string s = g_sym[i];
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      ulong ticket = PositionGetTicket(k);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == s &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
      {
         if(!trade.PositionClose(ticket))
            PrintFormat("ATTENZIONE: chiusura fallita su %s (%s)", s, trade.ResultRetcodeDescription());
      }
   }
}

void CloseAllOurPositions()
{
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      ulong ticket = PositionGetTicket(k);
      if(ticket == 0) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
         if(!trade.PositionClose(ticket))
            PrintFormat("ATTENZIONE: chiusura fallita per la posizione %I64u (%s)",
                        ticket, trade.ResultRetcodeDescription());
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
      PrintFormat("STOP DI EMERGENZA: drawdown oltre il %.1f%% (picco %.2f, equity %.2f). Chiudo tutto e mi fermo.",
                  InpMaxDrawdownPct, peak, equity);
      CloseAllOurPositions();
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

bool ExecWindowOK(MqlDateTime &dt)
{
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED)) return false;
   if(dt.day_of_week == 0 || dt.day_of_week == 6) return false;
   if(dt.hour < InpExecStartHour || dt.hour >= InpExecEndHour) return false;
   return true;
}

//+------------------------------------------------------------------+
//| Registro CSV e conteggi per mercato                              |
//+------------------------------------------------------------------+
int SymbolIndex(string s)
{
   for(int i = 0; i < g_n; i++) if(g_sym[i] == s) return i;
   return -1;
}

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
   int idx = SymbolIndex(HistoryDealGetString(deal, DEAL_SYMBOL));
   if(idx < 0) return;
   if(!IsOurDeal(deal)) return;

   double comm = HistoryDealGetDouble(deal, DEAL_COMMISSION);
   g_commissionSum += comm;
   g_net[idx] += HistoryDealGetDouble(deal, DEAL_PROFIT) + HistoryDealGetDouble(deal, DEAL_SWAP) + comm;

   if(InpLogToCSV) WriteDealToCSV(deal, g_sym[idx]);
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

void WriteDealToCSV(ulong deal, string s)
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

   int    digits  = (int)SymbolInfoInteger(s, SYMBOL_DIGITS);
   double point   = SymbolInfoDouble(s, SYMBOL_POINT);
   long   dType   = HistoryDealGetInteger(deal, DEAL_TYPE);
   long   dEntry  = HistoryDealGetInteger(deal, DEAL_ENTRY);
   long   dReason = HistoryDealGetInteger(deal, DEAL_REASON);
   string typeStr  = (dType == DEAL_TYPE_BUY) ? "BUY" : (dType == DEAL_TYPE_SELL ? "SELL" : "OTHER");
   string entryStr = (dEntry == DEAL_ENTRY_IN) ? "IN" : (dEntry == DEAL_ENTRY_OUT ? "OUT" : "OTHER");
   string offset   = g_isTester ? "" : IntegerToString((long)(TimeTradeServer() - TimeGMT()));

   MqlTick tick;
   double spreadPts = -1.0;
   if(SymbolInfoTick(s, tick) && point > 0.0) spreadPts = (tick.ask - tick.bid) / point;

   FileWrite(h,
             ModeString(), EA_VERSION,
             IntegerToString((long)deal),
             IntegerToString(HistoryDealGetInteger(deal, DEAL_POSITION_ID)),
             TimeToString((datetime)HistoryDealGetInteger(deal, DEAL_TIME), TIME_DATE | TIME_SECONDS),
             offset, s, typeStr, entryStr,
             EnumToString((ENUM_DEAL_REASON)dReason),
             DoubleToString(HistoryDealGetDouble(deal, DEAL_VOLUME), 2),
             DoubleToString(HistoryDealGetDouble(deal, DEAL_PRICE), digits),
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
   Comment(StringFormat("Nucleus EA v%s  |  %s  |  %d mercati\nStato: %s   Posizioni aperte: %d\nEquity: %.2f   Picco: %.2f\nRischio per mercato: %.2f%%   Drawdown max: %.1f%%",
                        EA_VERSION, ModeString(), g_n, state, CountOurPositionsAll(),
                        AccountInfoDouble(ACCOUNT_EQUITY), GetPeak(), InpRiskPct, InpMaxDrawdownPct));
}
//+------------------------------------------------------------------+
