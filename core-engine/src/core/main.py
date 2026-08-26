from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from ingest_seal.sealing import SealMismatchError

from core.auth.router import router as auth_router
from core.ingest.router import router as ingest_router
from core.routers.accounts import router as accounts_router
from core.routers.audit import router as audit_router
from core.routers.bots import router as bots_router
from core.routers.cemetery import router as cemetery_router
from core.routers.checklists import router as checklists_router
from core.routers.decisions import router as decisions_router
from core.routers.execution import router as execution_router
from core.routers.header import router as header_router
from core.routers.health import router as health_router
from core.routers.impulses import router as impulses_router
from core.routers.killswitch import router as killswitch_router
from core.routers.news import router as news_router
from core.routers.pipeline import router as pipeline_router
from core.routers.portfolio import router as portfolio_router
from core.routers.risk import router as risk_router
from core.routers.scaling import router as scaling_router
from core.routers.withdrawals import router as withdrawals_router

app = FastAPI(title="StratOS-QXPro core-engine")
app.include_router(ingest_router)
app.include_router(auth_router)
app.include_router(header_router)
app.include_router(decisions_router)
app.include_router(accounts_router)
app.include_router(bots_router)
app.include_router(portfolio_router)
app.include_router(health_router)
app.include_router(risk_router)
app.include_router(killswitch_router)
app.include_router(news_router)
app.include_router(execution_router)
app.include_router(pipeline_router)
app.include_router(cemetery_router)
app.include_router(impulses_router)
app.include_router(scaling_router)
app.include_router(audit_router)
app.include_router(withdrawals_router)
app.include_router(checklists_router)


@app.exception_handler(SealMismatchError)
async def seal_mismatch_handler(request: Request, exc: SealMismatchError) -> JSONResponse:
    """PARTE 6/9.1: sello invalido -> 422, fail-closed. `seal_and_create_batch`
    ya garantiza que nada se persiste antes de que esto se lance (la
    excepcion se levanta ANTES de crear la fila IngestBatch)."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": f"batch seal mismatch: expected={exc.expected} actual={exc.actual}"},
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "core-engine"}
