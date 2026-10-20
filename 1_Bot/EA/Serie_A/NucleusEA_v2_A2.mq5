//+------------------------------------------------------------------+
//|                                                NucleusEA_v2.mq5  |
//|                                                Progetto Nucleus  |
//+------------------------------------------------------------------+
//
// REGISTRO DEI TENTATIVI (onesta' statistica)
//   Tentativo 1: v1.1, incrocio EMA su H1, XAUUSD 2018-2022 -> BOCCIATO
//                (profitto -505.55, fattore di profitto 0.84, DD 10.03%)
//   Tentativo 2: questa versione.
//   Limite: massimo 3 tentativi sul periodo 2018-2022. Poi ci si ferma,
//   perche' ogni tentativo in piu' aumenta la probabilita' di trovare
//   per puro caso qualcosa che "sembra" funzionare.
//
// IDEA DELLA STRATEGIA (decisa PRIMA di guardare i dati)
//   Seguire le tendenze di medio periodo su grafico GIORNALIERO.
//   Base: studi accademici sul "time series momentum" (Moskowitz, Ooi,
//   Pedersen, 2012) e regole pubbliche del Sistema 1 dei Turtle.
//   Parametri presi dalle regole originali, NON ottimizzati da noi.
//
// REGOLE
//   - Entrata long:  la chiusura di ieri supera il massimo dei 20 giorni
//                    precedenti. Entrata short: scende sotto il minimo.
//   - Uscita:        la chiusura rompe il minimo (long) o il massimo
//                    (short) dei 10 giorni precedenti.
//   - Stop iniziale: 2 x ATR(20) giornaliero, sempre presente sul server.
//   - Nessun take profit: i guadagni vengono lasciati correre.
//   - Esecuzione solo in orario centrale (niente mezzanotte, spread alti).
//
// SEMPLIFICAZIONI PRUDENTI RISPETTO ALLE REGOLE ORIGINALI
//   - Segnale confermato sulla CHIUSURA giornaliera (niente falsi tocchi).
//   - Nessuna aggiunta di posizioni (niente piramidazione).
//   - Nessuna "regola di salto" del Sistema 1.
//   - Rischio 0.5% per operazione invece dell'1% originale.
//
// CRITERI DI VALUTAZIONE (scritti PRIMA del test, da non cambiare dopo)
//   Test sugli stessi parametri su 5 mercati: XAUUSD, EURUSD, GBPUSD,
//   USDJPY, AUDUSD, periodo 2018-2022.
//   1. Almeno 100 operazioni in totale sui 5 mercati.
//   2. Somma dei "Risultato dell'OnTester" (profitto con costi
//      raddoppiati, stimato dall'EA) positiva.
//   3. Profitto netto positivo in almeno 3 mercati su 5.
//   4. Nessun mercato con drawdown dell'equity pari o superiore al 10%.
//   Se anche un solo criterio fallisce: bocciato.
//   Se passa: verifica UNA volta sul 2023-oggi, poi 3 mesi di demo.
//
// NOTA SUI COSTI RADDOPPIATI
//   Lo Strategy Tester di MT5 non offre in modo semplice uno spread
//   fisso doppio. L'EA quindi somma, per ogni operazione, il costo di
//   UNO spread in piu' e delle commissioni una seconda volta, e sottrae
//   il totale dal profitto. Il valore appare nel report come
//   "Risultato dell'OnTester".
//
// SBLOCCO DELLO STOP DI EMERGENZA (solo su conto demo)
//   Strumenti > Variabili globali (F3): elimina NUCLEUS_EA_<magic>_HALT.
//+------------------------------------------------------------------+
#property copyright "Progetto Nucleus"
#property version   "2.00"
#property description "Trend following giornaliero (regole Turtle Sistema 1), solo DEMO."
#property description "Stima dei costi raddoppiati nel 'Risultato dell'OnTester'."

#include <Trade\Trade.mqh>

//--- LIMITI RIGIDI: non modificabili dagli input -------------------
#define HARD_MAX_RISK_PCT        1.0
#define HARD_MAX_DAILY_LOSS_PCT  3.0
#define HARD_MAX_DRAWDOWN_PCT   15.0
#define HARD_MAX_POSITIONS       5
#define SIGNAL_TF               PERIOD_D1
#define EA_VERSION              "2.00"

//--- INPUT -----------------------------------------------------------
input group "Strategia (regole originali, non ottimizzate)"
input int    InpEntryDays = 20;    // Entrata: rottura di N giorni
input int    InpExitDays  = 10;    // Uscita: rottura opposta di M giorni
input int    InpATRDays   = 20;    // Periodo ATR giornaliero
input double InpStopATR   = 2.0;   // Stop iniziale = ATR x questo valore

input group "Rischio"
input double InpRiskPct           = 0.5;  // Rischio per operazione (% saldo, max 1.0)
input double InpMaxDailyLossPct   = 2.0;  // Perdita giornaliera massima (%, max 3.0)
input double InpMaxDrawdownPct    = 10.0; // Drawdown per stop di emergenza (%, max 15)
input double InpMaxLots           = 1.0;  // Volume massimo assoluto (lotti)
input int    InpMaxTotalPositions = 3;    // Posizioni massime dell'EA su tutto il conto

input group "Esecuzione"
input int    InpExecStartHour        = 9;     // Ora di inizio esecuzione (ora server)
input int    InpExecEndHour          = 20;    // Ora di fine esecuzione (ora server)
input double InpMaxSpreadPctOfStop   = 10.0;  // Spread massimo (% della distanza dello stop)
input double InpMaxSlippagePctOfStop = 5.0;   // Slippage massimo (% della distanza dello stop)
input bool   InpCloseBeforeWeekend   = false; // Chiudi il venerdi' (sconsigliato su giornaliero)
input int    InpFridayCloseHour      = 20;    // Ora di chiusura del venerdi', se attiva

input group "Sicurezza e registro"
input bool   InpAllowRealAccount = false;         // Consenti conto REALE (lasciare false)
input ulong  InpMagic            = 20260925;      // Numero identificativo dell'EA
input bool   InpLogToCSV         = true;          // Scrivi il registro CSV
input string InpLogPrefix        = "Nucleus_EA2"; // Prefisso del file di registro

//--- VARIABILI GLOBALI -----------------------------------------------
CTrade   trade;
int      hATR = INVALID_HANDLE;

bool     g_isTester       = false;
datetime g_lastBarTime    = 0;
datetime g_currentDay     = 0;
double   g_dayStartEquity = 0.0;
double   g_startEquity    = 0.0;
double   g_peakMem        = 0.0;
bool     g_haltMem        = false;
string   g_gvPeak         = "";
string   g_gvHalt         = "";
string   g_logFile        = "";

int      g_pendingEntry   = 0;     // +1 comprare, -1 vendere, 0 nulla
bool     g_pendingExit    = false; // uscita da eseguire
datetime g_lastCloseTry   = 0;

double   g_extraCost      = 0.0;   // costo di uno spread in piu' per operazione
double   g_commissionSum  = 0.0;   // commissioni reali (negative)

int      g_signals        = 0;
int      g_opened         = 0;
int      g_skipMinVol     = 0;
int      g_skipExpired    = 0;     // segnale non eseguito entro la giornata
int      g_skipMaxPos     = 0;
int      g_skipOther      = 0;

//+------------------------------------------------------------------+
//| Avvio                                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   g_isTester = (bool)MQLInfoInteger(MQL_TESTER);

   //--- 1. Parametri contro i limiti rigidi
   if(InpRiskPct <= 0.0 || InpRiskPct > HARD_MAX_RISK_PCT)
   { Print("ERRORE: rischio per operazione fuori dai limiti."); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxDailyLossPct <= 0.0 || InpMaxDailyLossPct > HARD_MAX_DAILY_LOSS_PCT)
   { Print("ERRORE: perdita giornaliera fuori dai limiti."); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxDrawdownPct <= 0.0 || InpMaxDrawdownPct > HARD_MAX_DRAWDOWN_PCT)
   { Print("ERRORE: drawdown massimo fuori dai limiti."); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxTotalPositions < 1 || InpMaxTotalPositions > HARD_MAX_POSITIONS)
   { Print("ERRORE: numero massimo di posizioni fuori dai limiti."); return INIT_PARAMETERS_INCORRECT; }
   if(!(InpExitDays > 1 && InpEntryDays > InpExitDays))
   { Print("ERRORE: deve valere 1 < giorni di uscita < giorni di entrata."); return INIT_PARAMETERS_INCORRECT; }
   if(InpATRDays <= 0 || InpStopATR <= 0.0 || InpMaxLots <= 0.0)
   { Print("ERRORE: parametri di stop o volume non validi."); return INIT_PARAMETERS_INCORRECT; }
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

   //--- 3. Indicatore ATR giornaliero
   hATR = iATR(_Symbol, SIGNAL_TF, InpATRDays);
   if(hATR == INVALID_HANDLE)
   {
      Print("ERRORE: impossibile creare l'ATR.");
      return INIT_FAILED;
   }

   //--- 4. Esecuzione
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);

   //--- 5. Stato di rischio
   g_gvPeak = "NUCLEUS_EA_" + IntegerToString((long)InpMagic) + "_PEAK";
   g_gvHalt = "NUCLEUS_EA_" + IntegerToString((long)InpMagic) + "_HALT";
   g_startEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(GetPeak() <= 0.0)
      SetPeak(g_startEquity);

   //--- 6. Registro
   g_logFile = InpLogPrefix + "_" + ModeString() + "_" + _Symbol + ".csv";

   //--- 7. Il primo segnale si valuta alla prossima candela giornaliera
   g_lastBarTime = iTime(_Symbol, SIGNAL_TF, 0);

   PrintFormat("Nucleus EA v%s avviato su %s | modalita' %s | rischio %.2f%% | registro %s",
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
   double net = g_isTester ? TesterStatistics(STAT_PROFIT)
                           : AccountInfoDouble(ACCOUNT_EQUITY) - g_startEquity;
   double stress = net - (g_extraCost + MathAbs(g_commissionSum));

   PrintFormat("RIEPILOGO %s: segnali %d | aperti %d | scartati: lotto minimo %d, scaduti %d, limite posizioni %d, altro %d",
               _Symbol, g_signals, g_opened, g_skipMinVol, g_skipExpired, g_skipMaxPos, g_skipOther);
   PrintFormat("RIEPILOGO %s: profitto netto %.2f | con costi raddoppiati (stima) %.2f",
               _Symbol, net, stress);
   if(g_signals > 0 && g_skipMinVol * 2 > g_signals)
      Print("NOTA: piu' della meta' dei segnali e' stata scartata per il lotto minimo. "
            "Il saldo e' troppo piccolo per questo simbolo con il rischio impostato.");

   if(hATR != INVALID_HANDLE) IndicatorRelease(hATR);
   Comment("");
}

//--- Valore mostrato nel report come "Risultato dell'OnTester"
double OnTester()
{
   double net = TesterStatistics(STAT_PROFIT);
   return net - (g_extraCost + MathAbs(g_commissionSum));
}

//+------------------------------------------------------------------+
//| Ciclo principale                                                 |
//+------------------------------------------------------------------+
void OnTick()
{
   UpdateRiskState();
   if(!g_isTester) ShowStatus();
   if(IsHalted()) return;

   //--- Chiusura del venerdi' (solo se attivata)
   if(InpCloseBeforeWeekend && IsFridayCloseTime())
   {
      if(HasOpenPosition()) CloseOurPositionsThrottled();
      g_pendingEntry = 0;
      return;
   }

   //--- Nuova candela giornaliera: si calcolano i segnali
   if(IsNewBar())
      OnNewDailyBar();

   //--- Prima le uscite
   if(g_pendingExit)
   {
      if(!HasOpenPosition())
         g_pendingExit = false;              // gia' uscita (es. stop loss)
      else if(ExecWindowOK())
      {
         CloseOurPositionsThrottled();
         if(!HasOpenPosition()) g_pendingExit = false;
      }
   }

   //--- Poi le entrate
   if(g_pendingEntry != 0 && !g_pendingExit && !HasOpenPosition())
   {
      if(DailyLimitHit())
      { g_pendingEntry = 0; g_skipOther++; }
      else if(CountOurPositionsAllSymbols() >= InpMaxTotalPositions)
      { g_pendingEntry = 0; g_skipMaxPos++; }
      else if(ExecWindowOK())
      {
         int r = OpenTrade(g_pendingEntry);
         if(r != 0) g_pendingEntry = 0;      // aperta o abbandonata; 0 = riprova
      }
   }
}

void OnNewDailyBar()
{
   // Un segnale non eseguito entro la giornata precedente scade.
   if(g_pendingEntry != 0) g_skipExpired++;
   g_pendingEntry = 0;
   g_pendingExit  = false;

   long posType = -1;
   bool hasPos = GetOurPositionType(posType);

   if(hasPos && ExitSignal(posType))
      g_pendingExit = true;

   int sig = GetEntrySignal();
   if(sig == 0) return;

   // Se siamo gia' dentro nella stessa direzione, nessuna nuova entrata.
   if(hasPos && !g_pendingExit) return;

   g_pendingEntry = sig;
   g_signals++;
}

//+------------------------------------------------------------------+
//| Segnali: solo candele giornaliere CHIUSE                         |
//| Candela 1 = ieri. Canale calcolato sulle candele da 2 in poi.    |
//+------------------------------------------------------------------+
double ChannelHigh(int count)
{
   double arr[];
   if(CopyHigh(_Symbol, SIGNAL_TF, 2, count, arr) != count) return -1.0;
   return arr[ArrayMaximum(arr)];
}

double ChannelLow(int count)
{
   double arr[];
   if(CopyLow(_Symbol, SIGNAL_TF, 2, count, arr) != count) return -1.0;
   return arr[ArrayMinimum(arr)];
}

int GetEntrySignal()
{
   double close1 = iClose(_Symbol, SIGNAL_TF, 1);
   double hh = ChannelHigh(InpEntryDays);
   double ll = ChannelLow(InpEntryDays);
   if(close1 <= 0.0 || hh <= 0.0 || ll <= 0.0) return 0;
   if(close1 > hh) return  1;
   if(close1 < ll) return -1;
   return 0;
}

bool ExitSignal(long posType)
{
   double close1 = iClose(_Symbol, SIGNAL_TF, 1);
   double hh = ChannelHigh(InpExitDays);
   double ll = ChannelLow(InpExitDays);
   if(close1 <= 0.0 || hh <= 0.0 || ll <= 0.0) return false;
   if(posType == POSITION_TYPE_BUY  && close1 < ll) return true;
   if(posType == POSITION_TYPE_SELL && close1 > hh) return true;
   return false;
}

//+------------------------------------------------------------------+
//| Apertura: 1 = aperta, 0 = riprova piu' tardi, -1 = abbandona     |
//+------------------------------------------------------------------+
int OpenTrade(int signal)
{
   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(hATR, 0, 1, 1, atr) != 1 || atr[0] <= 0.0) return 0;

   double slDist  = atr[0] * InpStopATR;
   double minDist = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   if(slDist <= minDist)
   { Print("Operazione abbandonata: stop troppo vicino al minimo del broker."); g_skipOther++; return -1; }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick)) return 0;

   //--- Spread troppo alto: si riprova piu' tardi nella giornata
   double spread = tick.ask - tick.bid;
   if(spread < 0.0 || spread > slDist * InpMaxSpreadPctOfStop / 100.0) return 0;

   ulong devPoints = (ulong)MathMax(1.0, MathFloor(slDist * InpMaxSlippagePctOfStop / 100.0 / _Point));
   trade.SetDeviationInPoints(devPoints);

   double price = (signal > 0) ? tick.ask : tick.bid;
   double sl    = NormalizePrice((signal > 0) ? price - slDist : price + slDist);

   double vol = CalcVolume(signal, price, sl);
   if(vol <= 0.0) return -1;
   if(!MarginOK(signal, vol, price)) { g_skipOther++; return -1; }

   bool ok = (signal > 0)
             ? trade.Buy(vol,  _Symbol, price, sl, 0.0, "NucleusEA v2")
             : trade.Sell(vol, _Symbol, price, sl, 0.0, "NucleusEA v2");

   uint rc = trade.ResultRetcode();
   if(!ok || (rc != TRADE_RETCODE_DONE && rc != TRADE_RETCODE_PLACED))
   {
      PrintFormat("Ordine NON eseguito: codice %u (%s)", rc, trade.ResultRetcodeDescription());
      g_skipOther++;
      return -1;
   }

   g_opened++;

   //--- Stima prudente: un secondo spread pagato su questa operazione
   double sc = 0.0;
   if(OrderCalcProfit(ORDER_TYPE_BUY, _Symbol, vol, tick.ask, tick.bid, sc))
      g_extraCost += MathAbs(sc);

   PrintFormat("Aperta %s %.2f lotti a %s | SL %s | nessun TP",
               (signal > 0 ? "BUY" : "SELL"), vol,
               DoubleToString(trade.ResultPrice(), _Digits),
               DoubleToString(sl, _Digits));
   return 1;
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

   if(vol < vmin)
   {
      PrintFormat("Operazione saltata: il volume minimo (%.2f) supererebbe il rischio consentito.", vmin);
      g_skipMinVol++;
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

//+------------------------------------------------------------------+
//| Posizioni                                                        |
//+------------------------------------------------------------------+
bool IsOurPositionSelected()
{
   return (PositionGetString(POSITION_SYMBOL) == _Symbol &&
           (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic);
}

bool HasOpenPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetTicket(i) == 0) continue;
      if(IsOurPositionSelected()) return true;
   }
   return false;
}

bool GetOurPositionType(long &posType)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetTicket(i) == 0) continue;
      if(IsOurPositionSelected())
      {
         posType = PositionGetInteger(POSITION_TYPE);
         return true;
      }
   }
   return false;
}

int CountOurPositionsAllSymbols()
{
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetTicket(i) == 0) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic) n++;
   }
   return n;
}

void CloseOurPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(IsOurPositionSelected())
      {
         if(!trade.PositionClose(ticket))
            PrintFormat("ATTENZIONE: chiusura fallita per la posizione %I64u (%s)",
                        ticket, trade.ResultRetcodeDescription());
      }
   }
}

//--- Evita di ripetere i tentativi di chiusura a ogni tick
void CloseOurPositionsThrottled()
{
   if(TimeCurrent() - g_lastCloseTry < 60) return;
   g_lastCloseTry = TimeCurrent();
   CloseOurPositions();
}

//+------------------------------------------------------------------+
//| Stato di rischio                                                 |
//+------------------------------------------------------------------+
void UpdateRiskState()
{
   double   equity = AccountInfoDouble(ACCOUNT_EQUITY);
   datetime now    = TimeCurrent();
   datetime day    = now - (now % 86400);

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
      g_pendingEntry = 0;
      g_pendingExit  = false;
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

//+------------------------------------------------------------------+
//| Tempo                                                            |
//+------------------------------------------------------------------+
bool IsNewBar()
{
   datetime t = iTime(_Symbol, SIGNAL_TF, 0);
   if(t == 0 || t == g_lastBarTime) return false;
   g_lastBarTime = t;
   return true;
}

bool ExecWindowOK()
{
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED))
      return false;
   if(SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE) != SYMBOL_TRADE_MODE_FULL)
      return false;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(dt.day_of_week == 0 || dt.day_of_week == 6) return false;
   if(dt.hour < InpExecStartHour || dt.hour >= InpExecEndHour) return false;
   return true;
}

bool IsFridayCloseTime()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   return (dt.day_of_week == 5 && dt.hour >= InpFridayCloseHour);
}

//+------------------------------------------------------------------+
//| Registro CSV per Nucleus e conteggio commissioni                 |
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

   g_commissionSum += HistoryDealGetDouble(deal, DEAL_COMMISSION);

   if(InpLogToCSV)
      WriteDealToCSV(deal);
}

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

   MqlTick tick;
   double spreadPts = -1.0;
   if(SymbolInfoTick(_Symbol, tick) && _Point > 0.0)
      spreadPts = (tick.ask - tick.bid) / _Point;

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

   string pending = "nessuno";
   if(g_pendingExit)            pending = "uscita in attesa";
   else if(g_pendingEntry > 0)  pending = "acquisto in attesa";
   else if(g_pendingEntry < 0)  pending = "vendita in attesa";

   Comment(StringFormat("Nucleus EA v%s  |  %s  |  %s\nStato: %s   Segnale: %s\nEquity: %.2f   Picco: %.2f\nRischio: %.2f%%   Limite giorno: %.1f%%   Drawdown max: %.1f%%",
                        EA_VERSION, ModeString(), _Symbol, state, pending,
                        AccountInfoDouble(ACCOUNT_EQUITY), GetPeak(),
                        InpRiskPct, InpMaxDailyLossPct, InpMaxDrawdownPct));
}
//+------------------------------------------------------------------+
