from fastapi import APIRouter, Depends, HTTPException, Request

from api.auth import info_plan
from api.dependencies import obtener_usuario_actual
from api.limites import limitar
from api.schemas import CanjearRequest
from services.regalo_service import canjear_codigo

router = APIRouter(prefix="/suscripcion", tags=["Suscripción"])


@router.get("/")
def estado(usuario=Depends(obtener_usuario_actual)):
    return info_plan(int(usuario["cuenta_id"]))


@router.post("/canjear")
def canjear(
    datos: CanjearRequest,
    request: Request,
    usuario=Depends(obtener_usuario_actual),
):
    """Canjea un código de regalo en una cuenta ya existente."""

    limitar(
        f"canje:{usuario['id']}", 10, 3600,
        "Demasiados intentos con códigos.",
    )

    ok, mensaje = canjear_codigo(
        int(usuario["cuenta_id"]), int(usuario["id"]), datos.codigo
    )

    if not ok:
        raise HTTPException(422, mensaje)

    return {"ok": True, "mensaje": mensaje,
            "suscripcion": info_plan(int(usuario["cuenta_id"]))}
