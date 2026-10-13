from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import exigir_admin
from api.schemas import CodigoRegaloCreate, RegalarRequest
from services.regalo_service import (
    crear_codigo,
    desactivar_codigo,
    listar_codigos,
    regalar_a_email,
)

router = APIRouter(prefix="/admin", tags=["Administración"])


@router.get("/codigos")
def codigos(admin=Depends(exigir_admin)):
    return {"codigos": listar_codigos()}


@router.post("/codigos")
def nuevo_codigo(datos: CodigoRegaloCreate, admin=Depends(exigir_admin)):

    codigo, mensaje = crear_codigo(
        int(admin["id"]), datos.dias, datos.plan_slug,
        datos.usos_max, datos.vence_en_dias, datos.nota,
    )

    if codigo is None:
        raise HTTPException(422, mensaje)

    return {"codigo": codigo, "dias": datos.dias, "plan_slug": datos.plan_slug}


@router.delete("/codigos/{codigo_id}")
def quitar_codigo(codigo_id: int, admin=Depends(exigir_admin)):

    if not desactivar_codigo(codigo_id):
        raise HTTPException(404, "Código no encontrado")

    return {"ok": True}


@router.post("/regalar")
def regalar(datos: RegalarRequest, admin=Depends(exigir_admin)):

    ok, mensaje, _ = regalar_a_email(datos.email, datos.dias, datos.plan_slug)

    if not ok:
        raise HTTPException(422, mensaje)

    return {"ok": True, "mensaje": mensaje}
