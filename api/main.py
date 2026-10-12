import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import router as auth_router
from api.dashboard import router as dashboard_router
from api.movimientos import router as movimientos_router
from api.recordatorios import router as recordatorios_router

app = FastAPI(
    title="QUEDA API",
    description="API para Android, iOS y Web",
    version="1.1.0",
)

# La app móvil nativa no usa CORS; esto solo aplica si algún día
# consumes la API desde un navegador. Define API_CORS_ORIGINS="https://a.com,https://b.com"
_origenes = [o.strip() for o in os.getenv("API_CORS_ORIGINS", "").split(",") if o.strip()]
if _origenes:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origenes,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(movimientos_router)
app.include_router(recordatorios_router)


@app.get("/")
def root():
    return {"sistema": "QUEDA", "version": "1.1.0", "estado": "online"}


@app.get("/health")
def health():
    return {"status": "ok"}
