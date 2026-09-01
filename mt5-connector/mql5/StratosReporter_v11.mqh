#ifndef STRATOS_REPORTER_V11_MQH
#define STRATOS_REPORTER_V11_MQH
// StratOS EA reporter v1.1.  Sólo telemetría: NO incluye trade.mqh ni llama a
// OrderSend, CTrade, PositionOpen, PositionClose ni modifica órdenes.
// El EA escribe JSONL en FILE_COMMON; mt5-connector lo lee sin tocar los ficheros.

string StratosJsonEscape(const string value)
{
   string escaped=value;
   StringReplace(escaped,"\\","\\\\");
   StringReplace(escaped,"\"","\\\"");
   return escaped;
}

bool StratosAppendReporterEvent(const string filename,const string json_line)
{
   int handle=FileOpen(filename,FILE_COMMON|FILE_TXT|FILE_READ|FILE_WRITE|FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_ANSI);
   if(handle==INVALID_HANDLE) return false;
   FileSeek(handle,0,SEEK_END);
   FileWriteString(handle,json_line+"\r\n");
   FileFlush(handle);
   FileClose(handle);
   return true;
}

// El contrato HTTP exige ISO-8601 UTC. TimeToString() produce un formato de
// interfaz MT5 ("YYYY.MM.DD HH:MM:SS") que no es válido para el parser.
string StratosIsoUtc(const datetime timestamp_utc)
{
   MqlDateTime stamp;
   TimeToStruct(timestamp_utc,stamp);
   return StringFormat("%04d-%02d-%02dT%02d:%02d:%02dZ",stamp.year,stamp.mon,stamp.day,stamp.hour,stamp.min,stamp.sec);
}

// Llamar desde OnInit/OnTimer con los filtros y sizing realmente aplicados.
bool StratosReportEaState(const string filename,const string account_login,const long magic,
                          const string ea_version,const string mode,const bool autotrading,
                          const string schedule_filter_json,const string news_windows_json,
                          const double sizing_pct)
{
   string line=StringFormat("{\"batch_type\":\"ea_state\",\"account_login\":\"%s\",\"eas\":[{\"magic\":%I64d,\"ea_version\":\"%s\",\"mode\":\"%s\",\"autotrading\":%s,\"schedule_filter\":%s,\"news_windows\":%s,\"sizing_pct\":%.2f}]}",
                            StratosJsonEscape(account_login),magic,StratosJsonEscape(ea_version),StratosJsonEscape(mode),autotrading?"true":"false",schedule_filter_json,news_windows_json,sizing_pct);
   return StratosAppendReporterEvent(filename,line);
}

// Llamar tras recibir un resultado de ejecución real del EA. Slippage y TCA
// se calculan en core-engine; esta librería no emite ni reintenta órdenes.
bool StratosReportFill(const string filename,const string account_login,const long magic,
                       const string order_id,const string symbol,const string side,const double volume,
                       const double requested_price,const double executed_price,const double spread,const datetime ts)
{
   string line=StringFormat("{\"batch_type\":\"execution\",\"account_login\":\"%s\",\"magic\":%I64d,\"fills\":[{\"order_id\":\"%s\",\"symbol\":\"%s\",\"type\":\"%s\",\"volume\":%.4f,\"requested_price\":%.10f,\"executed_price\":%.10f,\"spread\":%.10f,\"ts\":\"%s\"}]}",
                            StratosJsonEscape(account_login),magic,StratosJsonEscape(order_id),StratosJsonEscape(symbol),side,volume,requested_price,executed_price,spread,StratosIsoUtc(ts));
   return StratosAppendReporterEvent(filename,line);
}

// Llamar cuando el EA recibe un resultado rechazado del servidor. El reporter
// no reintenta ni modifica la orden: deja únicamente una evidencia auditable.
bool StratosReportRejectedOrder(const string filename,const string account_login,const long magic,
                                const string order_id,const string symbol,const string side,const double volume,
                                const double requested_price,const string rejection_reason,const datetime ts_utc)
{
   string line=StringFormat("{\"batch_type\":\"execution\",\"account_login\":\"%s\",\"magic\":%I64d,\"fills\":[{\"order_id\":\"%s\",\"symbol\":\"%s\",\"type\":\"%s\",\"volume\":%.4f,\"requested_price\":%.10f,\"status\":\"REJECTED\",\"rejection_reason\":\"%s\",\"ts\":\"%s\"}]}",
                            StratosJsonEscape(account_login),magic,StratosJsonEscape(order_id),StratosJsonEscape(symbol),side,volume,requested_price,StratosJsonEscape(rejection_reason),StratosIsoUtc(ts_utc));
   return StratosAppendReporterEvent(filename,line);
}

#endif // STRATOS_REPORTER_V11_MQH
