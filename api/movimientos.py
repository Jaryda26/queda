from fastapi import APIRouter, Depends, HTTPException

from db import obtener_dataframe, ejecutar_query
from api.dependencies import usuario_con_plan
from api.schemas import MovimientoCreate

router = APIRouter(prefix="/movimientos", tags=["Movimientos"])


@router.get("/")
def listar_movimientos(usuario=Depends(usuario_con_plan)):

    df = obtener_dataframe(
        """
        SELECT id, fecha, tipo, concepto, categoria, monto, origen_ingreso
        FROM gastos.movimientos
        WHERE cuenta_id = :cuenta_id
        ORDER BY fecha DESC, id DESC
        LIMIT 100
        """,
        {"cuenta_id": usuario["cuenta_id"]}
    )

    return df.fillna("").astype({"fecha": str}).to_dict(orient="records")


@router.get("/resumen")
def resumen_movimientos(usuario=Depends(usuario_con_plan)):

    df = obtener_dataframe(
        """
        SELECT COALESCE(SUM(monto), 0) AS total
        FROM gastos.movimientos
        WHERE cuenta_id = :cuenta_id AND tipo = 'GASTO'
          AND DATE_TRUNC('month', fecha) = DATE_TRUNC('month', CURRENT_DATE)
        """,
        {"cuenta_id": usuario["cuenta_id"]}
    )

    total = float(df.iloc[0]["total"])
    return {"mensaje": f"Has gastado {total:,.2f} pesos este mes"}


@router.get("/categoria/{categoria}")
def por_categoria(categoria: str, usuario=Depends(usuario_con_plan)):
    # Busca en categoría Y concepto (antes solo concepto).
    df = obtener_dataframe(
        """
        SELECT COALESCE(SUM(monto), 0) AS total
        FROM gastos.movimientos
        WHERE cuenta_id = :cuenta_id AND tipo = 'GASTO'
          AND (LOWER(concepto) LIKE :q OR LOWER(categoria) LIKE :q)
        """,
        {"cuenta_id": usuario["cuenta_id"], "q": f"%{categoria.lower()}%"}
    )

    total = float(df.iloc[0]["total"])
    return {"mensaje": f"Has gastado {total:,.2f} pesos en {categoria}"}


@router.post("/")
def guardar_movimiento(m: MovimientoCreate, usuario=Depends(usuario_con_plan)):

    tipo = m.tipo.strip().upper()
    if tipo not in ("GASTO", "INGRESO"):
        raise HTTPException(422, "tipo debe ser GASTO o INGRESO")

    ejecutar_query(
        """
        INSERT INTO gastos.movimientos
            (usuario_id, cuenta_id, tipo, concepto, categoria, monto,
             origen_ingreso, texto_original)
        VALUES
            (:uid, :cid, :tipo, :concepto, :categoria, :monto,
             :origen, :texto)
        """,
        {
            "uid": usuario["id"],
            "cid": usuario["cuenta_id"],
            "tipo": tipo,
            "concepto": m.concepto.strip(),
            "categoria": m.categoria.strip() or "Otros",
            "monto": m.monto,
            "origen": m.origen_ingreso,
            "texto": f"App móvil: {m.concepto.strip()}",
        }
    )

    return {"success": True, "mensaje": "Movimiento registrado"}


@router.delete("/{movimiento_id}")
def borrar_movimiento(movimiento_id: int, usuario=Depends(usuario_con_plan)):
    # Borrar un movimiento restituye el saldo automáticamente porque el
    # saldo se calcula sumando movimientos (igual que en la web).
    r = ejecutar_query(
        "DELETE FROM gastos.movimientos WHERE id = :id AND cuenta_id = :cid",
        {"id": movimiento_id, "cid": usuario["cuenta_id"]}
    )

    if r.rowcount == 0:
        raise HTTPException(404, "Movimiento no encontrado")

    return {"success": True, "mensaje": "Movimiento eliminado"}
