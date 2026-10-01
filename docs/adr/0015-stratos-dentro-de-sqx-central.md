# ADR 0015 — StratOS dentro de SQX Central: supervisión y UI incrustada, sin reescribir sus vistas

## Contexto

El 2026-09-30 el operador decidió que SQX Central (`Apps_entorno_SQX/sqx_central`, puerto 8760), la app que gobierna
el resto del entorno SQX, integre también StratOS, con el plan de reescribir sus vistas dentro de Central. El plan de
Central (`sqx_central/docs/PLAN_SQX_CENTRAL.md`) dejó esa fase (F7) bloqueada hasta que el operador la confirmara y
existiera este ADR, porque choca con reglas de este proyecto:

- **P12 / P15.13**: fidelidad visual 1:1 con `capturas_proyecto_dashboard/`; toda desviación necesita su ADR.
- **Arquitectura sagrada**: lógica de negocio solo en `core-engine`; el frontend no lleva reglas.
- **Auth** (ADR 0007): el JWT del usuario lo valida `core-engine`; no hay token de servicio. Un cliente externo solo
  puede leer con una sesión de usuario, y las credenciales no las maneja ningún agente.
- **Cuentas reales** (JJTI, BEPB): estrictamente read-only; las cuentas son independientes y no se suman.

## Decisión

1. **StratOS sigue siendo el sistema de registro y su UI (React, 12 pestañas) la única superficie de negocio.** No se
   reimplementan pestañas ni reglas en Central.
2. **Central supervisa el stack en solo lectura**: estado de los contenedores `stratos_operational-*` (salud, puertos)
   y si el frontend responde en el host. No arranca, para ni recrea contenedores de StratOS; eso sigue siendo
   `StratOS_Stack_Operacional.bat`.
3. **Central incrusta la UI real de StratOS** (iframe sobre el puerto 5473) en una pestaña "StratOS". El inicio de
   sesión lo hace el operador en esa propia UI; Central no ve ni guarda credenciales ni tokens. El `nginx.conf` del
   frontend no declara `X-Frame-Options` ni `frame-ancestors`, por lo que no se toca.
4. **Vistas nativas en Central (futuras, no incluidas aquí)** solo si se cumple todo: (a) solo lectura, `GET` a
   `api-gateway`; (b) con un token de sesión que pegue el operador en memoria, sin persistirlo y sin cambiar la auth de
   StratOS (ADR 0007 se mantiene); (c) cada cuenta por separado, sin totales; (d) los datos y reglas vienen tal cual de
   `core-engine`; (e) un ADR por vista que documente su desviación respecto a las capturas.

## Consecuencias

- No hay segunda copia de la lógica de negocio ni de las 12 pestañas que mantener.
- La integración es de supervisión y acceso, no de reescritura: el operador entra a StratOS desde Central pero con la UI
  y la sesión de StratOS.
- La reescritura nativa de pestañas queda diferida con condiciones explícitas (punto 4); no se ha implementado ni
  verificado ninguna.
- Central muestra el estado del stack aunque el frontend no responda en el host (p. ej. si el reenvío de puertos de
  Docker falla), y lo declara en vez de ocultarlo.
