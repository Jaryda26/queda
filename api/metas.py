from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import usuario_con_plan
from services import metas_service as ms

router = APIRouter(prefix="/metas", tags=["Metas de ahorro"])


class MetaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    monto_objetivo: float = Field(gt=0)
    fecha_limite: Optional[date] = None


class AbonoIn(BaseModel):
    # Positivo = abono; negativo = retiro.
    monto: float


def _falla_tablas(e):
    # Casi siempre: falta correr sql/metas_ia.sql en Supabase.
    raise HTTPException(
        503, "Las metas de ahorro no están disponibles todavía."
    ) from e


@router.get("/")
def listar(usuario=Depends(usuario_con_plan)):
    try:
        metas = ms.listar_metas(usuario["cuenta_id"])
    except Exception as e:
        _falla_tablas(e)

    return {"metas": metas}


@router.post("/", status_code=201)
def crear(datos: MetaIn, usuario=Depends(usuario_con_plan)):
    try:
        return ms.crear_meta(
            usuario["id"], usuario["cuenta_id"], datos.nombre,
            datos.monto_objetivo, datos.fecha_limite,
        )
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        _falla_tablas(e)


@router.post("/{meta_id}/abonos")
def abonar(meta_id: int, datos: AbonoIn, usuario=Depends(usuario_con_plan)):
    try:
        return ms.abonar(
            usuario["id"], usuario["cuenta_id"], meta_id, datos.monto
        )
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        _falla_tablas(e)


@router.delete("/{meta_id}")
def eliminar(meta_id: int, usuario=Depends(usuario_con_plan)):
    try:
        ok = ms.eliminar_meta(usuario["cuenta_id"], meta_id)
    except Exception as e:
        _falla_tablas(e)

    if not ok:
        raise HTTPException(404, "No encontré esa meta.")

    return {"ok": True}
