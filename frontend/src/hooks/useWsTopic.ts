import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { useAuthStore } from "@/stores/authStore";
import { ReconnectingSocket, type SocketStatus } from "@/ws/wsClient";

const WS_BASE_URL: string = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8100";

export type WsTopic = "equity" | "alerts" | "pipeline" | "health";

// Invalida queryKey en cada mensaje del topic (el WS solo dispara "hay
// novedad, refresca ya" -- REST sigue siendo la unica fuente de forma de
// los datos, PARTE 9.3). No sustituye el polling propio de cada query
// (p.ej. useHeaderSummary ya tiene refetchInterval:5000 como base siempre
// activa, PARTE 7.1 "fallback polling 5s") -- esto solo acelera el
// refresco cuando el WS SI esta vivo, no es la unica via de frescura.
export function useWsTopic(topic: WsTopic, queryKey: unknown[]): SocketStatus {
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((state) => state.accessToken);
  const [status, setStatus] = useState<SocketStatus>("connecting");

  useEffect(() => {
    if (!accessToken) {
      return;
    }
    const url = `${WS_BASE_URL}/ws/${topic}?token=${encodeURIComponent(accessToken)}`;
    const socket = new ReconnectingSocket(
      url,
      () => queryClient.invalidateQueries({ queryKey }),
      setStatus
    );
    return () => socket.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topic, accessToken]);

  return status;
}
