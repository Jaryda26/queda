import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.admin import router as admin_router
from api.aprendizaje import router as aprendizaje_router
from api.auth import router as auth_router
from api.dashboard import router as dashboard_router
from api.movimientos import router as movimientos_router
from api.presupuesto import router as presupuesto_router
from api.recordatorios import router as recordatorios_router
from api.suscripcion import router as suscripcion_router
from api.voz import router as voz_router

# En producción (API_ENV=prod) se oculta la documentación interactiva.
_prod = os.getenv("API_ENV", "").strip().lower() == "prod"

app = FastAPI(
    title="QUEDA API",
    description="API para Android, iOS y Web",
    version="1.2.0",
    docs_url=None if _prod else "/docs",
    redoc_url=None,
    openapi_url=None if _prod else "/openapi.json",
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
app.include_router(presupuesto_router)
app.include_router(aprendizaje_router)
app.include_router(voz_router)
app.include_router(suscripcion_router)
app.include_router(admin_router)


@app.get("/")
def root():
    return {"sistema": "QUEDA", "version": "1.2.0", "estado": "online"}


@app.get("/health")
def health():
    return {"status": "ok"}
