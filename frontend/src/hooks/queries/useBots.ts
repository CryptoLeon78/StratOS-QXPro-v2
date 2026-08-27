import { useQuery } from "@tanstack/react-query";

import { getBot, getBots, getBotSemaphoreHistory } from "@/api/endpoints/bots";

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
