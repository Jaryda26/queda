from fastapi import APIRouter, Depends, HTTPException

from db import obtener_dataframe, ejecutar_query
from api.dependencies import usuario_con_plan
from api.schemas import RecordatorioCreate
from services.recordatorios_service import (
    marcar_pagado,
    puede_agregar_recordatorio,
)

router = APIRouter(prefix="/recordatorios", tags=["Recordatorios"])

FRECUENCIAS = ("UNICO", "SEMANAL", "QUINCENAL", "MENSUAL", "ANUAL")


def _obtener(recordatorio_id, cuenta_id):
    df = obtener_dataframe(
        """
        SELECT * FROM gastos.recordatorios
        WHERE id = :id AND cuenta_id = :cid
        """,
        {"id": recordatorio_id, "cid": cuenta_id}
    )
    if df.empty:
        raise HTTPException(404, "Recordatorio no encontrado")
    return df.iloc[0]


@router.get("/")
def listar_recordatorios(usuario=Depends(usuario_con_plan)):

    df = obtener_dataframe(
        """
        SELECT id, descripcion, monto, fecha_vencimiento, frecuencia,
               dias_anticipacion, pagado, tipo
        FROM gastos.recordatorios
        WHERE cuenta_id = :cid
        ORDER BY pagado, fecha_vencimiento NULLS LAST, id
        """,
        {"cid": usuario["cuenta_id"]}
    )

    df["fecha_vencimiento"] = df["fecha_vencimiento"].astype(str).replace(
        {"NaT": "", "None": ""}
    )

    return df.fillna("").to_dict(orient="records")


@router.get("/pendientes")
def pendientes(usuario=Depends(usuario_con_plan)):

    df = obtener_dataframe(
        """
        SELECT COUNT(*) AS total FROM gastos.recordatorios
        WHERE cuenta_id = :cid AND pagado = FALSE
        """,
        {"cid": usuario["cuenta_id"]}
    )

    total = int(df.iloc[0]["total"])

    if total == 0:
        return {"mensaje": "No tienes recordatorios pendientes"}

    return {"mensaje": f"Tienes {total} recordatorios pendientes"}


@router.post("/")
def crear_recordatorio(r: RecordatorioCreate, usuario=Depends(usuario_con_plan)):

    tipo = r.tipo.strip().upper()
    frecuencia = r.frecuencia.strip().upper()

    if tipo not in ("PAGO", "ACTIVIDAD"):
        raise HTTPException(422, "tipo debe ser PAGO o ACTIVIDAD")
    if frecuencia not in FRECUENCIAS:
        raise HTTPException(422, f"frecuencia debe ser una de {FRECUENCIAS}")

    # Mismo tope por plan que la web (Básico = 5).
    ok, mensaje = puede_agregar_recordatorio(usuario["cuenta_id"])
    if not ok:
        raise HTTPException(403, mensaje)

    ejecutar_query(
        """
        INSERT INTO gastos.recordatorios
            (usuario_id, cuenta_id, descripcion, tipo, monto,
             fecha_vencimiento, frecuencia, dias_anticipacion, pagado)
        VALUES
            (:uid, :cid, :descripcion, :tipo, :monto,
             :fecha, :frecuencia, :dias, FALSE)
        """,
        {
            "uid": usuario["id"],
            "cid": usuario["cuenta_id"],
            "descripcion": r.descripcion.strip(),
            "tipo": tipo,
            "monto": (r.monto or 0) if tipo == "PAGO" else None,
            "fecha": r.fecha_vencimiento,
            "frecuencia": frecuencia,
            "dias": r.dias_anticipacion,
        }
    )

    return {"success": True, "mensaje": "Recordatorio registrado"}


@router.put("/{recordatorio_id}/pagar")
def pagar_recordatorio(recordatorio_id: int, usuario=Depends(usuario_con_plan)):
    """
    Igual que el botón de la web:
    - PAGO: registra el GASTO (categoría 'Recordatorio').
    - ACTIVIDAD: solo se completa, sin dinero.
    - Recurrente: avanza la fecha al siguiente periodo; único: queda pagado.
    """

    fila = _obtener(recordatorio_id, usuario["cuenta_id"])

    if bool(fila["pagado"]):
        raise HTTPException(409, "Ese recordatorio ya estaba completado")

    if str(fila.get("tipo") or "PAGO").upper() == "PAGO":
        monto = fila["monto"]
        if monto == monto and monto is not None and float(monto) > 0:
            ejecutar_query(
                """
                INSERT INTO gastos.movimientos
                    (usuario_id, cuenta_id, tipo, categoria, concepto,
                     monto, texto_original)
                VALUES
                    (:uid, :cid, 'GASTO', 'Recordatorio', :concepto,
                     :monto, :texto)
                """,
                {
                    "uid": usuario["id"],
                    "cid": usuario["cuenta_id"],
                    "concepto": fila["descripcion"],
                    "monto": float(monto),
                    "texto": f"Pago de {fila['descripcion']} (app móvil)",
                }
            )

    fecha = fila["fecha_vencimiento"]
    sin_fecha = fecha is None or fecha != fecha
    marcar_pagado(
        int(fila["id"]),
        None if sin_fecha else fecha,
        # Sin fecha no se puede calcular la siguiente: se trata como único.
        "UNICO" if sin_fecha else str(fila["frecuencia"] or "UNICO").upper(),
    )

    return {"success": True, "mensaje": "Recordatorio completado"}


@router.put("/{recordatorio_id}/despues")
def posponer_recordatorio(recordatorio_id: int, usuario=Depends(usuario_con_plan)):

    _obtener(recordatorio_id, usuario["cuenta_id"])

    ejecutar_query(
        """
        UPDATE gastos.recordatorios
        SET fecha_proxima_alerta = CURRENT_DATE + INTERVAL '1 day'
        WHERE id = :id AND cuenta_id = :cid
        """,
        {"id": recordatorio_id, "cid": usuario["cuenta_id"]}
    )

    return {"success": True, "mensaje": "Te lo recordaré mañana"}


@router.delete("/{recordatorio_id}")
def borrar_recordatorio(recordatorio_id: int, usuario=Depends(usuario_con_plan)):

    r = ejecutar_query(
        "DELETE FROM gastos.recordatorios WHERE id = :id AND cuenta_id = :cid",
        {"id": recordatorio_id, "cid": usuario["cuenta_id"]}
    )

    if r.rowcount == 0:
        raise HTTPException(404, "Recordatorio no encontrado")

    return {"success": True, "mensaje": "Recordatorio eliminado"}
