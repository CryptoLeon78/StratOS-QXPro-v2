from fastapi import FastAPI

app = FastAPI(title="StratOS-QXPro core-engine")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "core-engine"}
