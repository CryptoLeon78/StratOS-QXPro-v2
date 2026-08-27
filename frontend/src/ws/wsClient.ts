// PARTE 9.3: WS con auth por query param (?token=, el navegador no puede
// fijar cabeceras en el handshake -- ws/auth.py de core-engine). Backoff
// exponencial con tope: 1,2,4,8,16s, maximo 30s. Tras 3 fallos de conexion
// consecutivos se declara "down" (el consumidor cae a polling, PARTE 7.1)
// y sigue reintentando en background cada 30s por si vuelve.
const BACKOFF_STEPS_MS = [1000, 2000, 4000, 8000, 16000];
const BACKOFF_MAX_MS = 30000;
const DOWN_AFTER_FAILURES = 3;

export type SocketStatus = "connecting" | "open" | "down";

export class ReconnectingSocket {
  private socket: WebSocket | null = null;
  private consecutiveFailures = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private closedByCaller = false;
  private status: SocketStatus = "connecting";

  constructor(
    private readonly url: string,
    private readonly onMessage: () => void,
    private readonly onStatusChange: (status: SocketStatus) => void
  ) {
    this.connect();
  }

  private setStatus(status: SocketStatus) {
    if (this.status !== status) {
      this.status = status;
      this.onStatusChange(status);
    }
  }

  private connect() {
    if (this.closedByCaller) {
      return;
    }
    const socket = new WebSocket(this.url);
    this.socket = socket;

    socket.onopen = () => {
      this.consecutiveFailures = 0;
      this.setStatus("open");
    };

    socket.onmessage = () => {
      this.onMessage();
    };

    socket.onclose = () => {
      this.consecutiveFailures += 1;
      this.setStatus(this.consecutiveFailures >= DOWN_AFTER_FAILURES ? "down" : "connecting");
      this.scheduleReconnect();
    };

    socket.onerror = () => {
      socket.close();
    };
  }

  private scheduleReconnect() {
    if (this.closedByCaller) {
      return;
    }
    const delay =
      this.status === "down"
        ? BACKOFF_MAX_MS
        : (BACKOFF_STEPS_MS[this.consecutiveFailures - 1] ?? BACKOFF_MAX_MS);
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }

  close() {
    this.closedByCaller = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    this.socket?.close();
  }
}
