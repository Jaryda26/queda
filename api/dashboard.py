from fastapi import APIRouter, Depends

from api.dependencies import usuario_con_plan
from api.dashboard_service import obtener_tendencia
from services.insights_service import kpis_periodo

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/resumen")
def resumen(usuario=Depends(usuario_con_plan)):

    # Mismo periodo que el presupuesto y que la voz (antes era el mes
    # calendario y no cuadraba con "cuánto llevo").
    k = kpis_periodo(usuario["cuenta_id"])

    return {
        # Nombres que ya usa la app (ahora son DEL PERIODO):
        "ingresos_mes": k["ingresos"],
        "gastos_mes": k["gastos"],
        "ahorro_mes": k["resultado"],
        "movimientos": k["movimientos"],
        # Nuevos:
        "periodo_etiqueta": k["etiqueta"],
        "periodo_inicio": k["inicio"].isoformat(),
        "periodo_fin": k["fin"].isoformat(),
        "tiene_presupuesto": k["tiene_presupuesto"],
        "saldo_acumulado": k["saldo_acumulado"],
    }


@router.get("/categorias")
def categorias(usuario=Depends(usuario_con_plan)):

    k = kpis_periodo(usuario["cuenta_id"])

    return [{"categoria": c, "total": t} for c, t in k["categorias"]]


@router.get("/tendencia")
def tendencia(usuario=Depends(usuario_con_plan)):

    df = obtener_tendencia(usuario["cuenta_id"]).fillna(0)
    return df.to_dict(orient="records")
