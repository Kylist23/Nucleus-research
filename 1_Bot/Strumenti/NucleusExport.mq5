//+------------------------------------------------------------------+
//|                                              NucleusExport.mq5   |
//|                                                Progetto Nucleus  |
//+------------------------------------------------------------------+
// Non opera. Durante un test nello Strategy Tester salva ogni candela
// chiusa del timeframe del test in un CSV nella cartella comune
// Nucleus, per le analisi in Python. Usare solo fino al 2022.12.31:
// i dati dal 2023 sono la cassaforte e restano intatti.
//+------------------------------------------------------------------+
#property copyright "Progetto Nucleus"
#property version   "1.00"
#property description "Esporta lo storico delle candele in CSV. Non apre operazioni."

int      g_file = INVALID_HANDLE;
datetime g_lastBar = 0;
long     g_rows = 0;

int OnInit()
{
   string name = "Nucleus\\" + _Symbol + "_" + EnumToString(_Period) + ".csv";
   StringReplace(name, "PERIOD_", "");
   g_file = FileOpen(name, FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON, ',');
   if(g_file == INVALID_HANDLE)
   { PrintFormat("ERRORE: impossibile creare %s (errore %d)", name, GetLastError()); return INIT_FAILED; }
   FileWrite(g_file, "time", "open", "high", "low", "close", "tick_volume", "spread_points");
   PrintFormat("Esportazione avviata: %s", name);
   return INIT_SUCCEEDED;
}

void OnTick()
{
   datetime t0 = iTime(_Symbol, _Period, 0);
   if(t0 == 0 || t0 == g_lastBar) return;
   g_lastBar = t0;

   MqlRates r[];
   if(CopyRates(_Symbol, _Period, 1, 1, r) != 1) return;   // ultima candela CHIUSA
   FileWrite(g_file, TimeToString(r[0].time, TIME_DATE | TIME_MINUTES),
             DoubleToString(r[0].open, _Digits), DoubleToString(r[0].high, _Digits),
             DoubleToString(r[0].low, _Digits), DoubleToString(r[0].close, _Digits),
             IntegerToString(r[0].tick_volume), IntegerToString(r[0].spread));
   g_rows++;
}

void OnDeinit(const int reason)
{
   if(g_file != INVALID_HANDLE) FileClose(g_file);
   PrintFormat("Esportazione terminata: %I64d candele salvate.", g_rows);
}
//+------------------------------------------------------------------+
