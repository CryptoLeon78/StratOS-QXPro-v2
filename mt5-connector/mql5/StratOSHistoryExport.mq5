// Read-only account-history exporter. It never sends, modifies or closes orders.
#property strict
#property script_show_inputs

input datetime InpFrom = D'2018.01.01 00:00';
input string InpOutputFile = "StratOS/history_deals.csv";

string CsvEscape(const string value)
{
   string escaped = value;
   StringReplace(escaped, "\"", "\"\"");
   return "\"" + escaped + "\"";
}

void OnStart()
{
   const datetime until = TimeCurrent();
   if(!HistorySelect(InpFrom, until))
   {
      Print("StratOS history export: HistorySelect failed: ", GetLastError());
      return;
   }
   const int handle = FileOpen(InpOutputFile, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(handle == INVALID_HANDLE)
   {
      Print("StratOS history export: FileOpen failed: ", GetLastError());
      return;
   }
   FileWrite(handle, "deal_ticket", "position_id", "time", "magic", "symbol", "entry", "type", "volume", "price", "profit", "commission", "swap", "reason");
   const uint total = HistoryDealsTotal();
   for(uint index = 0; index < total; index++)
   {
      const ulong ticket = HistoryDealGetTicket(index);
      if(ticket == 0)
         continue;
      const long entry = HistoryDealGetInteger(ticket, DEAL_ENTRY);
      const long type = HistoryDealGetInteger(ticket, DEAL_TYPE);
      if((entry != DEAL_ENTRY_IN && entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_INOUT) ||
         (type != DEAL_TYPE_BUY && type != DEAL_TYPE_SELL))
         continue;
      FileWrite(handle,
         (string)ticket,
         (string)HistoryDealGetInteger(ticket, DEAL_POSITION_ID),
         TimeToString((datetime)HistoryDealGetInteger(ticket, DEAL_TIME), TIME_DATE | TIME_SECONDS),
         (string)HistoryDealGetInteger(ticket, DEAL_MAGIC),
         CsvEscape(HistoryDealGetString(ticket, DEAL_SYMBOL)),
         (string)entry,
         (string)type,
         DoubleToString(HistoryDealGetDouble(ticket, DEAL_VOLUME), 2),
         DoubleToString(HistoryDealGetDouble(ticket, DEAL_PRICE), _Digits),
         DoubleToString(HistoryDealGetDouble(ticket, DEAL_PROFIT), 2),
         DoubleToString(HistoryDealGetDouble(ticket, DEAL_COMMISSION), 2),
         DoubleToString(HistoryDealGetDouble(ticket, DEAL_SWAP), 2),
         (string)HistoryDealGetInteger(ticket, DEAL_REASON));
   }
   FileClose(handle);
   Print("StratOS history export complete: ", total, " deals, ", InpOutputFile);
}
