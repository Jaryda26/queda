from fastapi import APIRouter, Depends

from api.dependencies import usuario_con_plan
from api.dashboard_service import (
    obtener_resumen_dashboard,
    obtener_gastos_por_categoria,
    obtener_tendencia,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/resumen")
def resumen(usuario=Depends(usuario_con_plan)):

    df = obtener_resumen_dashboard(usuario["cuenta_id"])

    ingresos = float(df.loc[df["tipo"].str.upper() == "INGRESO", "monto"].sum())
    gastos = float(df.loc[df["tipo"].str.upper() == "GASTO", "monto"].sum())

    return {
        "ingresos_mes": ingresos,
        "gastos_mes": gastos,
        "ahorro_mes": ingresos - gastos,
        "movimientos": int(len(df)),
    }


@router.get("/categorias")
def categorias(usuario=Depends(usuario_con_plan)):

    df = obtener_gastos_por_categoria(usuario["cuenta_id"]).fillna("")
    return df.to_dict(orient="records")


@router.get("/tendencia")
def tendencia(usuario=Depends(usuario_con_plan)):

    df = obtener_tendencia(usuario["cuenta_id"]).fillna(0)
    return df.to_dict(orient="records")
