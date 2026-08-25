# Arquitectura — StratOS-QXPro

Topología de 2 nodos (PARTE 3 del prompt maestro). El paquete `MetaTrader5` solo funciona en Windows con terminal instalado; Wine queda fuera de scope.

```mermaid
flowchart LR
    subgraph NodoA["Nodo A — VPS Windows (Alemania)"]
        MT5R["MT5 REAL"]
        MT5D["MT5 DEMO (cantera)"]
        CONN["mt5-connector\n(read-only, buffer SQLite,\nsello SHA-256 por lote)"]
        MT5R --> CONN
        MT5D --> CONN
    end

    subgraph NodoB["Nodo B — VPS Linux (docker-compose)"]
        NGINX["nginx (+Certbot)"]
        GW["api-gateway\nJWT · rate limit · WS broker"]
        CORE["core-engine\nFastAPI async"]
        WORKER["worker + scheduler (ARQ)"]
        PG["postgres 16 + TimescaleDB"]
        REDIS["redis 7\ncache + PubSub + broker ARQ"]
        FE["frontend (React)"]
        PROM["prometheus + grafana (opcional)"]

        NGINX --> FE
        NGINX --> GW
        GW --> CORE
        CORE --> PG
        CORE --> REDIS
        WORKER --> PG
        WORKER --> REDIS
        CORE -.metrics.-> PROM
    end

    CONN -- "HTTPS outbound + X-API-Key\n(cero puertos entrantes)" --> GW
    Operador(["Operador"]) -- "HTTPS + WSS, JWT" --> NGINX
    CORE -- "HTTPS outbound" --> TG["Telegram"]
```

Reglas de esta topología (P1–P15):
- El conector SOLO inicia conexión saliente hacia el gateway; nunca hay puertos entrantes en el VPS Windows.
- El conector es estrictamente read-only: nunca envía órdenes a MT5 (P4).
- El frontend solo habla con `api-gateway` (P15.5); `api-gateway` es el único punto de entrada JWT + WS hacia `core-engine`.
- `core-engine` es el único lugar con lógica de dominio (semáforos, kill-switch, pipeline, fórmulas); `api-gateway` no tiene reglas de negocio, el conector no tiene reglas de negocio.

En G0 solo se define la topología completa en `docker-compose.yml`; el contenido real de `core-engine`/`api-gateway`/`frontend` llega en G1–G8, y `mt5-connector`/`mt5-simulator` en G4.
