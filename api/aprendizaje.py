from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from api.dependencies import usuario_con_plan
from services.aprendizaje_service import (
    eliminar_frase,
    guardar_frase,
    listar_frases,
)

router = APIRouter(prefix="/aprendizaje", tags=["Aprendizaje"])


class FraseIn(BaseModel):
    frase: str
    accion: str
    categoria: Optional[str] = None


@router.get("/")
def listar(usuario=Depends(usuario_con_plan)):

    df = listar_frases(usuario["cuenta_id"])

    frases = [
        {
            "id": int(f["id"]),
            "frase": str(f["frase"]),
            "accion": str(f["accion"]),
            "categoria": (str(f["categoria"]) if f["categoria"] else None),
        }
        for _, f in df.iterrows()
    ]

    return {"frases": frases}


@router.post("/")
def crear(datos: FraseIn, usuario=Depends(usuario_con_plan)):

    try:
        _, actualizada = guardar_frase(
            usuario["id"], usuario["cuenta_id"],
            datos.frase, datos.accion, datos.categoria,
        )
    except ValueError as e:
        raise HTTPException(422, str(e))

    return {"ok": True, "actualizada": actualizada}


@router.delete("/{frase_id}")
def borrar(frase_id: int, usuario=Depends(usuario_con_plan)):

    if not eliminar_frase(usuario["cuenta_id"], frase_id):
        raise HTTPException(404, "Frase no encontrada")

    return {"ok": True}
