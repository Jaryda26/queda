"""
Presupuesto de la cuenta, con periodos de CALENDARIO:

  SEMANAL   -> 7 días desde el día de la semana que elijas (p. ej. de
               viernes a jueves si te pagan los viernes).
  QUINCENAL -> del 1 al 15 y del 16 al último día del mes.
  MENSUAL   -> del 1 al último día del mes (28/29/30/31).

El periodo se calcula SIEMPRE a partir de la fecha de hoy: no hay que
renovar nada ni se reinicia al editar el monto.
"""

import calendar
from datetime import date, timedelta

from db import ejecutar_query, obtener_dataframe

DIAS_PERIODO = {"SEMANAL": 7, "QUINCENAL": 15, "MENSUAL": 30}

NOMBRES_DIA = [
    "lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo",
]

MONTO_MAXIMO = 1_000_000_000


def _fecha(valor):
    return valor.date() if hasattr(valor, "date") else valor


def _ultimo(cuenta_id):
    """Última fila del presupuesto; dia_inicio=0 si aún no existe la columna."""

    try:
        return obtener_dataframe(
            """
            SELECT id, tipo_periodo, monto, fecha_inicio, fecha_fin,
                   dia_inicio
            FROM gastos.presupuestos
            WHERE cuenta_id = :cuenta_id
            ORDER BY id DESC
            LIMIT 1
            """,
            {"cuenta_id": cuenta_id},
        )
    except Exception:
        df = obtener_dataframe(
            """
            SELECT id, tipo_periodo, monto, fecha_inicio, fecha_fin
            FROM gastos.presupuestos
            WHERE cuenta_id = :cuenta_id
            ORDER BY id DESC
            LIMIT 1
            """,
            {"cuenta_id": cuenta_id},
        )
        df["dia_inicio"] = 0
        return df


def periodo_para(tipo, dia_inicio=0, hoy=None):
    """(inicio, fin) del periodo de calendario que contiene a 'hoy'."""

    hoy = hoy or date.today()
    tipo = str(tipo or "MENSUAL").upper()

    if tipo == "SEMANAL":
        dia = int(dia_inicio or 0) % 7
        inicio = hoy - timedelta(days=(hoy.weekday() - dia) % 7)
        return inicio, inicio + timedelta(days=6)

    ultimo = calendar.monthrange(hoy.year, hoy.month)[1]

    if tipo == "QUINCENAL":
        if hoy.day <= 15:
            return hoy.replace(day=1), hoy.replace(day=15)
        return hoy.replace(day=16), hoy.replace(day=ultimo)

    return hoy.replace(day=1), hoy.replace(day=ultimo)


def periodo_anterior(tipo, dia_inicio, inicio_actual):
    """Periodo inmediato anterior al que empieza en 'inicio_actual'."""

    return periodo_para(tipo, dia_inicio, inicio_actual - timedelta(days=1))


def obtener_estado_presupuesto(cuenta_id):
    """None si la cuenta aún no define presupuesto."""

    df = _ultimo(cuenta_id)

    if df.empty:
        return None

    fila = df.iloc[0]
    tipo = str(fila["tipo_periodo"] or "MENSUAL").upper()
    monto = float(fila["monto"] or 0)

    try:
        dia = int(fila["dia_inicio"])
    except (TypeError, ValueError):
        dia = 0

    hoy = date.today()
    inicio, fin = periodo_para(tipo, dia, hoy)

    gastado = obtener_dataframe(
        """
        SELECT COALESCE(SUM(monto),0) AS total
        FROM gastos.movimientos
        WHERE tipo='GASTO' AND cuenta_id = :cuenta_id
          AND fecha::date BETWEEN :inicio AND :fin
        """,
        {"cuenta_id": cuenta_id, "inicio": inicio, "fin": fin},
    )

    gastado = float(gastado.iloc[0]["total"]) if not gastado.empty else 0.0

    return {
        "tipo_periodo": tipo,
        "monto": monto,
        "dia_inicio": dia,
        "nombre_dia_inicio": NOMBRES_DIA[dia % 7],
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": fin.isoformat(),
        "gastado": round(gastado, 2),
        "restante": round(monto - gastado, 2),
        "porcentaje": round(gastado / monto * 100, 1) if monto > 0 else 0.0,
        # Días que quedan contando HOY (el último día del periodo es 1).
        "dias_restantes": max((fin - hoy).days + 1, 0),
        "periodo_reiniciado": False,
    }


def guardar_presupuesto(usuario_id, cuenta_id, tipo_periodo, monto,
                        dia_inicio=None):
    """
    Crea o actualiza (igual que la web). dia_inicio (0=lunes ... 6=domingo)
    solo importa en SEMANAL; si no se da, se conserva el anterior.
    Lanza ValueError si algo es inválido.
    """

    tipo = str(tipo_periodo or "").upper()

    if tipo not in DIAS_PERIODO:
        raise ValueError("Periodo inválido (SEMANAL, QUINCENAL o MENSUAL).")

    try:
        monto = round(float(monto), 2)
    except (TypeError, ValueError):
        raise ValueError("Monto inválido.")

    if not (0 <= monto <= MONTO_MAXIMO):
        raise ValueError("Monto fuera de rango.")

    df = _ultimo(cuenta_id)

    if dia_inicio is None:
        dia_inicio = int(df.iloc[0]["dia_inicio"]) if not df.empty else 0

    try:
        dia_inicio = int(dia_inicio)
    except (TypeError, ValueError):
        raise ValueError("Día de inicio inválido.")

    if not (0 <= dia_inicio <= 6):
        raise ValueError("Día de inicio inválido.")

    inicio, fin = periodo_para(tipo, dia_inicio)

    params = {
        "usuario_id": usuario_id, "cuenta_id": cuenta_id, "tipo": tipo,
        "monto": monto, "inicio": inicio, "fin": fin, "dia": dia_inicio,
    }

    try:
        if df.empty:
            ejecutar_query(
                """
                INSERT INTO gastos.presupuestos
                    (usuario_id, cuenta_id, tipo_periodo, monto,
                     fecha_inicio, fecha_fin, dia_inicio)
                VALUES
                    (:usuario_id, :cuenta_id, :tipo, :monto,
                     :inicio, :fin, :dia)
                """,
                params,
            )
        else:
            ejecutar_query(
                """
                UPDATE gastos.presupuestos
                SET tipo_periodo = :tipo, monto = :monto,
                    fecha_inicio = :inicio, fecha_fin = :fin,
                    dia_inicio = :dia
                WHERE id = :id AND cuenta_id = :cuenta_id
                """,
                {**params, "id": int(df.iloc[0]["id"])},
            )
    except Exception:
        # Falta correr sql/periodos.sql (columna dia_inicio): se guarda
        # sin ella y la semana arranca en lunes.
        if df.empty:
            ejecutar_query(
                """
                INSERT INTO gastos.presupuestos
                    (usuario_id, cuenta_id, tipo_periodo, monto,
                     fecha_inicio, fecha_fin)
                VALUES
                    (:usuario_id, :cuenta_id, :tipo, :monto, :inicio, :fin)
                """,
                params,
            )
        else:
            ejecutar_query(
                """
                UPDATE gastos.presupuestos
                SET tipo_periodo = :tipo, monto = :monto,
                    fecha_inicio = :inicio, fecha_fin = :fin
                WHERE id = :id AND cuenta_id = :cuenta_id
                """,
                {**params, "id": int(df.iloc[0]["id"])},
            )

    return obtener_estado_presupuesto(cuenta_id)


def cambiar_dia_inicio(usuario_id, cuenta_id, dia_inicio):
    """Solo cambia el día en que inicia la semana (conserva tipo y monto)."""

    df = _ultimo(cuenta_id)

    if df.empty:
        raise ValueError(
            "Primero crea tu presupuesto, por ejemplo: pon mi presupuesto "
            "semanal en 2000 pesos."
        )

    return guardar_presupuesto(
        usuario_id, cuenta_id, "SEMANAL",
        float(df.iloc[0]["monto"] or 0), dia_inicio,
    )
