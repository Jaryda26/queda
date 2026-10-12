from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.dependencies import usuario_con_plan
from api.voz_service import procesar, texto_para_voz
from services.billing_service import obtener_plan_actual

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


def _hora_mexico():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Mexico_City"))
    except Exception:
        # Windows sin el paquete tzdata: UTC-6 fijo (México ya no usa horario de verano).
        return datetime.now(timezone(timedelta(hours=-6)))


@router.get("/saludo")
def saludo(usuario=Depends(usuario_con_plan)):
    """
    Saludo automático al abrir la app (igual que en la web): buenos días +
    nombre + resumen con cifras calculadas en Python y redactado por la IA
    si el plan la incluye. Nunca falla: si algo se cae, regresa solo el saludo.
    """

    hora = _hora_mexico().hour
    parte = (
        "Buenos días" if hora < 12
        else "Buenas tardes" if hora < 19
        else "Buenas noches"
    )

    partes_nombre = str(usuario.get("nombre") or "").split()
    nombre = partes_nombre[0] if partes_nombre else ""
    encabezado = f"{parte} {nombre}".strip()

    narrativa = ""

    try:
        from services.narrativa_service import generar_narrativa_ia

        plan = obtener_plan_actual(usuario["cuenta_id"])
        usar_ia = bool(plan is not None and plan.get("incluye_ia", True))

        narrativa = generar_narrativa_ia(usuario["cuenta_id"], usar_ia=usar_ia)
    except Exception:
        narrativa = ""

    return {
        "saludo": encabezado,
        "narrativa": narrativa,
        "voz": texto_para_voz(f"{encabezado}. {narrativa}".strip()),
    }
