import { Server, WebSocket as MockWebSocket } from "mock-socket";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ReconnectingSocket } from "@/ws/wsClient";

const URL = "ws://localhost:12345/ws/equity";

beforeEach(() => {
  vi.stubGlobal("WebSocket", MockWebSocket);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ReconnectingSocket", () => {
  it("llama a onMessage con cada frame recibido y reporta status 'open'", async () => {
    const server = new Server(URL);
    const onMessage = vi.fn();
    const onStatusChange = vi.fn();
    const socket = new ReconnectingSocket(URL, onMessage, onStatusChange);

    server.on("connection", (client) => {
      client.send("hola");
    });

    await vi.waitFor(() => expect(onMessage).toHaveBeenCalledTimes(1));
    expect(onStatusChange).toHaveBeenCalledWith("open");

    socket.close();
    server.stop();
  });

  it("un fallo de conexion nunca reporta status 'open'", async () => {
    // Nadie escucha en este puerto -- el connect falla de verdad,
    // disparando onclose (y setStatus no notifica "connecting" de nuevo:
    // ya es el estado inicial, solo notifica en TRANSICIONES reales).
    const onMessage = vi.fn();
    const onStatusChange = vi.fn();
    const socket = new ReconnectingSocket("ws://localhost:1/ws/equity", onMessage, onStatusChange);

    await new Promise((resolve) => setTimeout(resolve, 300));

    expect(onStatusChange).not.toHaveBeenCalledWith("open");
    expect(onMessage).not.toHaveBeenCalled();
    socket.close();
  });
});
