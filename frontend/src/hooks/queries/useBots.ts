import { useQuery } from "@tanstack/react-query";

import {
  getBot,
  getBotMetrics,
  getBotOpenPositions,
  getBotPnlCurve,
  getBotRMultiples,
  getBots,
  getBotSemaphoreHistory,
} from "@/api/endpoints/bots";

export function useBots() {
  return useQuery({ queryKey: ["bots"], queryFn: getBots });
}

export function useBot(botId: number | undefined) {
  return useQuery({
    queryKey: ["bot", botId],
    queryFn: () => getBot(botId!),
    enabled: botId !== undefined,
  });
}

export function useBotSemaphoreHistory(botId: number | undefined) {
  return useQuery({
    queryKey: ["bot-semaphore-history", botId],
    queryFn: () => getBotSemaphoreHistory(botId!),
    enabled: botId !== undefined,
  });
}

export function useBotMetrics(botId: number | undefined) {
  return useQuery({
    queryKey: ["bot-metrics", botId],
    queryFn: () => getBotMetrics(botId!),
    enabled: botId !== undefined,
  });
}

export function useBotPnlCurve(botId: number | undefined) {
  return useQuery({
    queryKey: ["bot-pnl-curve", botId],
    queryFn: () => getBotPnlCurve(botId!),
    enabled: botId !== undefined,
  });
}

export function useBotRMultiples(botId: number | undefined) {
  return useQuery({
    queryKey: ["bot-r-multiples", botId],
    queryFn: () => getBotRMultiples(botId!),
    enabled: botId !== undefined,
  });
}

export function useBotOpenPositions(botId: number | undefined) {
  return useQuery({
    queryKey: ["bot-open-positions", botId],
    queryFn: () => getBotOpenPositions(botId!),
    enabled: botId !== undefined,
  });
}
