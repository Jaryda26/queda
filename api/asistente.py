"""
Chat con el asesor (celular). Orden: comandos y consultas calculadas
(gratis) -> registro por reglas -> asesor con IA (gasta 1 del cupo diario;
el plan Básico recibe la versión calculada).
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import usuario_con_plan
from api.voz_service import procesar
from services.billing_service import obtener_plan_actual
from services.plan_ia_service import estado_ia
from services.usuario_service import actualizar_nombre_agente

router = APIRouter(prefix="/asistente", tags=["Asistente"])


class Turno(BaseModel):
    rol: str = Field(pattern="^(usuario|asistente)$")
    texto: str = Field(max_length=1500)


class ChatIn(BaseModel):
    mensaje: str = Field(min_length=1, max_length=500)
    historial: Optional[List[Turno]] = None


class NombreIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=50)


def _estado(usuario):
    plan = obtener_plan_actual(usuario["cuenta_id"])
    return {
        "nombre_agente": usuario.get("nombre_agente") or "Queda",
        **estado_ia(usuario["cuenta_id"], plan),
    }


@router.get("/estado")
def estado(usuario=Depends(usuario_con_plan)):
    return _estado(usuario)


@router.post("/chat")
def chat(c: ChatIn, usuario=Depends(usuario_con_plan)):
    historial = [t.model_dump() for t in (c.historial or [])]
    r = procesar(usuario, c.mensaje, False, modo_chat=True, historial=historial)
    r["cupo"] = _estado(usuario)
    return r


@router.put("/nombre")
def nombre(n: NombreIn, usuario=Depends(usuario_con_plan)):
    ok, msg = actualizar_nombre_agente(int(usuario["id"]), n.nombre)
    if not ok:
        raise HTTPException(422, msg)
    usuario["nombre_agente"] = n.nombre.strip()
    return {"mensaje": msg, **_estado(usuario)}
