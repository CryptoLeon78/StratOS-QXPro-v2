# Placeholder de G0 (ver ASSUMPTIONS.md G0-04): sin JWT, rate limit ni WS broker
# todavia. Implementacion real segun PARTE 3/CLAUDE.md llega en G5, cuando
# core-engine expone la API 9.2 que este gateway debe proxear/agregar.
from fastapi import FastAPI

app = FastAPI(title="StratOS-QXPro api-gateway")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "api-gateway"}
