#ifndef STRATOS_REPORTER_ADAPTER_V11_MQH
#define STRATOS_REPORTER_ADAPTER_V11_MQH
// Adaptador para EAs SQX gestionados. Sólo escucha sus callbacks MT5 y escribe
// JSONL; no usa CTrade, OrderSend ni modifica órdenes existentes.
#include <StratOS/StratosReporter_v11.mqh>

struct StratosPendingRequest {
   bool active;
   ulong order_id;
   string symbol;
   string side;
   double volume;
   double requested_price;
   double spread;
};

StratosPendingRequest stratos_pending_request;

bool StratosReporterManagedOnInit(const string filename,const long magic,const string ea_version,
                                  const bool limit_time_range,const string range_from,const string range_to,
                                  const string operational_mode,const double sizing_pct)
{
   string account_login=IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));
   bool autotrading=(TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)!=0 && MQLInfoInteger(MQL_TRADE_ALLOWED)!=0);
   string schedule=StringFormat("{\"limit_time_range\":%s,\"from\":\"%s\",\"to\":\"%s\"}",
                                limit_time_range?"true":"false",StratosJsonEscape(range_from),StratosJsonEscape(range_to));
   string mode=operational_mode;
   StringToUpper(mode);
   if(mode!="REAL" && mode!="PAPER") mode="PAPER";
   return StratosReportEaState(filename,account_login,magic,ea_version,mode,autotrading,schedule,"[]",sizing_pct);
}

bool StratosReporterIsMarketOrder(const ENUM_ORDER_TYPE order_type)
{
   return order_type==ORDER_TYPE_BUY || order_type==ORDER_TYPE_SELL;
}

string StratosReporterSide(const ENUM_ORDER_TYPE order_type)
{
   return order_type==ORDER_TYPE_BUY ? "BUY" : "SELL";
}

void StratosReporterManagedOnTradeTransaction(const string filename,const long magic,
                                               const MqlTradeTransaction &transaction,
                                               const MqlTradeRequest &request,
                                               const MqlTradeResult &result)
{
   if(transaction.type==TRADE_TRANSACTION_REQUEST && request.magic==magic && StratosReporterIsMarketOrder(request.type))
   {
      stratos_pending_request.active=true;
      stratos_pending_request.order_id=result.order;
      stratos_pending_request.symbol=request.symbol;
      stratos_pending_request.side=StratosReporterSide(request.type);
      stratos_pending_request.volume=request.volume;
      stratos_pending_request.requested_price=request.price;
      stratos_pending_request.spread=(double)SymbolInfoInteger(request.symbol,SYMBOL_SPREAD)*_Point;
      return;
   }
   if(transaction.type!=TRADE_TRANSACTION_DEAL_ADD || !stratos_pending_request.active || !HistoryDealSelect(transaction.deal)) return;
   if((long)HistoryDealGetInteger(transaction.deal,DEAL_MAGIC)!=magic) return;
   ulong deal_order=(ulong)HistoryDealGetInteger(transaction.deal,DEAL_ORDER);
   if(stratos_pending_request.order_id!=0 && deal_order!=stratos_pending_request.order_id) return;
   long entry=HistoryDealGetInteger(transaction.deal,DEAL_ENTRY);
   if(entry!=DEAL_ENTRY_IN) return;
   string account_login=IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));
   StratosReportFill(filename,account_login,magic,StringFormat("%I64u",transaction.deal),
                     stratos_pending_request.symbol,stratos_pending_request.side,stratos_pending_request.volume,
                     stratos_pending_request.requested_price,HistoryDealGetDouble(transaction.deal,DEAL_PRICE),
                     stratos_pending_request.spread,TimeGMT());
   stratos_pending_request.active=false;
}

#endif // STRATOS_REPORTER_ADAPTER_V11_MQH
