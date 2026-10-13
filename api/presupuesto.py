from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from pydantic import BaseModel, Field

from api.dependencies import usuario_con_plan
from services.presupuesto_service import (
    guardar_presupuesto,
    obtener_estado_presupuesto,
)

router = APIRouter(prefix="/presupuesto", tags=["Presupuesto"])


class PresupuestoIn(BaseModel):
    tipo_periodo: str
    monto: float
    # Solo SEMANAL: 0=lunes ... 4=viernes ... 6=domingo. Sin valor se
    # conserva el que ya tenía (lunes la primera vez).
    dia_inicio: Optional[int] = Field(default=None, ge=0, le=6)


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
            datos.tipo_periodo, datos.monto, datos.dia_inicio,
        )
    except ValueError as e:
        raise HTTPException(422, str(e))

    return {"existe": True, "presupuesto": estado}
