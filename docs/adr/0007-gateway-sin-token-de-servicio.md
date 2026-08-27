# 0007 — api-gateway: proxy pass-through, sin "token de servicio" propio

## Contexto

PARTE 3 del prompt maestro especifica una tabla de autenticación entre componentes (`doc_app/PROMPT_MAESTRO.md`, línea 132):

| Origen | Destino | Protocolo | Auth | Propósito |
|---|---|---|---|---|
| api-gateway | core-engine | HTTP red docker | **token de servicio** | proxy/agregación |
| Navegador | api-gateway | HTTPS + WSS | JWT access+refresh | UI |

Es decir: el navegador se autentica ante el gateway con el JWT del usuario, y el gateway debería autenticarse ante core-engine con una credencial DISTINTA (un "token de servicio" propio del gateway) — no reenviar el JWT del usuario tal cual.

G9 construyó `api-gateway/` como un proxy transparente (`gateway/proxy.py`): reenvía cualquier `/{path:path}` a `core-engine` preservando headers, incluido `Authorization` intacto. **No implementa ningún token de servicio** — no valida el JWT él mismo, no extrae la identidad del usuario, no la reenvía por un header de confianza distinto.

## Decisión

Se mantiene el diseño pass-through ya construido y verificado (ASSUMPTIONS G9-00), sin token de servicio, por estas razones:

1. **El gateway nunca necesita `JWT_SECRET`**: si validara el JWT él mismo para luego reenviar la identidad por otro canal, necesitaría el mismo secreto de firma que core-engine — un segundo proceso con el secreto de auth más sensible del sistema, sin necesidad real (core-engine ya lo valida en cada request).
2. **Superficie de ataque no mayor**: la red `api-gateway ↔ core-engine` es la red interna de `docker-compose` (nunca expuesta fuera del Nodo B) — el mismo nivel de aislamiento que ya usan `worker`/`scheduler` para hablar con `postgres`/`redis` sin ninguna capa de credencial adicional sobre la de la propia BBDD/broker.
3. **Una sola fuente de verdad de auth**: implementar un token de servicio real exigiría que el gateway VALIDARA el JWT (para poder extraer y reenviar la identidad), reintroduciendo exactamente la duplicación que el diseño actual evita a propósito.
4. **Alcance**: la alternativa (gateway valida JWT + headers de confianza `X-User-Id`/`X-User-Role` protegidos por un `GATEWAY_SERVICE_TOKEN` compartido, `get_current_user` de core-engine con un segundo camino de confianza) toca la dependencia de auth que usan TODAS las rutas protegidas del sistema — cambio de arquitectura real, no una pieza aislada de "hardening", evaluado y rechazado para esta fase por el operador.

## Consecuencias

- El JWT del usuario viaja tal cual por la red interna docker hasta core-engine — aceptable dado el aislamiento de red del punto 2, pero es una desviación real y consciente de la tabla de PARTE 3.
- Si en el futuro el Nodo B deja de ser una red docker-compose aislada (p.ej. gateway y core-engine en hosts físicos distintos, o se añade un tercer componente no confiable en la misma red), este ADR queda obsoleto y el token de servicio real pasa a ser necesario — revisar entonces.
- `ASSUMPTIONS.md` G9-00 ya documentaba la decisión de diseño; este ADR es su contraparte formal para la tabla de PARTE 3 (regla P15.13: ninguna desviación de una decisión de arquitectura fijada sin su ADR correspondiente).
