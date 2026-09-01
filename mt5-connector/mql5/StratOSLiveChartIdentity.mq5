// One-shot read-only inventory of currently open MT5 charts.
#property strict
#property script_show_inputs

input string InpOutputFile = "StratOSLiveChartIdentity.csv";

void OnStart()
{
   int file = FileOpen(InpOutputFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ';');
   if(file == INVALID_HANDLE)
   {
      Print("StratOS identity export failed: ", GetLastError());
      return;
   }
   FileWrite(file, "chart_id", "symbol", "timeframe", "expert_name");
   long chart_id = ChartFirst();
   while(chart_id >= 0)
   {
      string expert_name = "";
      ChartGetString(chart_id, CHART_EXPERT_NAME, expert_name);
      FileWrite(file, (string)chart_id, ChartSymbol(chart_id),
                EnumToString((ENUM_TIMEFRAMES)ChartPeriod(chart_id)), expert_name);
      chart_id = ChartNext(chart_id);
   }
   FileClose(file);
   Print("StratOS identity export completed: ", InpOutputFile);
}
