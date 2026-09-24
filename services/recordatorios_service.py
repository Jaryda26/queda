import calendar
from datetime import date, timedelta

from db import ejecutar_query, obtener_dataframe
from services.billing_service import obtener_plan_actual


def contar_recordatorios_activos(cuenta_id):

    df = obtener_dataframe(
        """
        SELECT COUNT(*) AS total
        FROM gastos.recordatorios
        WHERE cuenta_id = :cuenta_id AND pagado = FALSE
        """,
        {"cuenta_id": cuenta_id}
    )

    return int(df.iloc[0]["total"])


def puede_agregar_recordatorio(cuenta_id):
    """
    Revisa el tope de recordatorios activos del plan de la cuenta
    (lo comparten el formulario manual y la creación por voz).
    Regresa (True, None) si se puede agregar uno más, o
    (False, mensaje) si ya se llegó al límite.
    """

    plan = obtener_plan_actual(cuenta_id)

    limite = (
        plan.get("limite_recordatorios")
        if plan is not None else None
    )

    if limite is None:
        return True, None

    activos = contar_recordatorios_activos(cuenta_id)

    if activos >= limite:

        return False, (
            f"Llegaste al límite de {limite} recordatorios "
            f"activos de tu plan. Paga o borra alguno, o sube "
            f"de plan en 💳 Suscripción."
        )

    return True, None


def calcular_siguiente_fecha(fecha_actual, frecuencia):
    """
    Devuelve la siguiente fecha de vencimiento según la frecuencia,
    o None si la frecuencia es UNICO (no se repite).
    """

    frecuencia = str(frecuencia).upper()

    if frecuencia == "SEMANAL":
        return fecha_actual + timedelta(days=7)

    if frecuencia == "QUINCENAL":
        return fecha_actual + timedelta(days=15)

    if frecuencia == "MENSUAL":
        return _sumar_meses(fecha_actual, 1)

    if frecuencia == "ANUAL":
        return _sumar_meses(fecha_actual, 12)

    return None


def _sumar_meses(fecha_actual, meses):

    mes_total = fecha_actual.month - 1 + meses
    anio = fecha_actual.year + mes_total // 12
    mes = mes_total % 12 + 1

    ultimo_dia_mes = calendar.monthrange(anio, mes)[1]
    dia = min(fecha_actual.day, ultimo_dia_mes)

    return date(anio, mes, dia)


def marcar_pagado(row_id, fecha_vencimiento, frecuencia):
    """
    Marca un recordatorio como pagado.

    - Si es UNICO: pagado = TRUE definitivamente.
    - Si es recurrente (SEMANAL/QUINCENAL/MENSUAL/ANUAL): avanza
      fecha_vencimiento al siguiente periodo y lo deja pendiente
      de nuevo (pagado = FALSE), para que vuelva a aparecer cuando
      se acerque la próxima fecha.
    """

    siguiente = calcular_siguiente_fecha(
        fecha_vencimiento,
        frecuencia
    )

    if siguiente is None:

        ejecutar_query(
            """
            UPDATE gastos.recordatorios
            SET
                pagado = TRUE,
                fecha_ultimo_pago = CURRENT_DATE
            WHERE id = :id
            """,
            {"id": row_id}
        )

    else:

        ejecutar_query(
            """
            UPDATE gastos.recordatorios
            SET
                fecha_ultimo_pago = CURRENT_DATE,
                fecha_vencimiento = :siguiente,
                pagado = FALSE
            WHERE id = :id
            """,
            {
                "id": row_id,
                "siguiente": siguiente
            }
        )
