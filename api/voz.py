from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.dependencies import usuario_con_plan
from api.voz_service import procesar

router = APIRouter(prefix="/voz", tags=["Voz"])


class ComandoVoz(BaseModel):
    texto: str = Field(min_length=1, max_length=500)
    # El servidor no guarda estado: si la respuesta anterior pidió un monto
    # (esperando_monto=true), el teléfono lo manda de vuelta aquí.
    esperando_monto: bool = False


@router.post("/comando")
def comando(c: ComandoVoz, usuario=Depends(usuario_con_plan)):
    # Endpoint síncrono: FastAPI lo corre en un hilo; el estado de cada
    # petición es propio de su hilo (ver services/estado_voz.py).
    return procesar(usuario, c.texto, c.esperando_monto)
