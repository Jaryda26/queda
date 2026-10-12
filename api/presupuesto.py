from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.dependencies import usuario_con_plan
from services.presupuesto_service import (
    guardar_presupuesto,
    obtener_estado_presupuesto,
)

router = APIRouter(prefix="/presupuesto", tags=["Presupuesto"])


class PresupuestoIn(BaseModel):
    tipo_periodo: str
    monto: float


@router.get("/")
def ver_presupuesto(usuario=Depends(usuario_con_plan)):

    estado = obtener_estado_presupuesto(usuario["cuenta_id"])

    return {"existe": estado is not None, "presupuesto": estado}


@router.put("/")
def cambiar_presupuesto(
    datos: PresupuestoIn, usuario=Depends(usuario_con_plan)
):

    try:
        estado = guardar_presupuesto(
            usuario["id"], usuario["cuenta_id"],
            datos.tipo_periodo, datos.monto,
        )
    except ValueError as e:
        raise HTTPException(422, str(e))

    return {"existe": True, "presupuesto": estado}
