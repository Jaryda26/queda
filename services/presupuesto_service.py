"""
Presupuesto de la cuenta. Misma lógica que views/presupuesto.py (la fila
más reciente por cuenta; SEMANAL=7, QUINCENAL=15, MENSUAL=30 días), pero
reutilizable desde la API móvil y desde los comandos de voz.
"""

from datetime import date, timedelta

from db import ejecutar_query, obtener_dataframe

DIAS_PERIODO = {"SEMANAL": 7, "QUINCENAL": 15, "MENSUAL": 30}

MONTO_MAXIMO = 1_000_000_000


def _fecha(valor):
    return valor.date() if hasattr(valor, "date") else valor


def _ultimo(cuenta_id):
    return obtener_dataframe(
        """
        SELECT id, tipo_periodo, monto, fecha_inicio, fecha_fin
        FROM gastos.presupuestos
        WHERE cuenta_id = :cuenta_id
        ORDER BY id DESC
        LIMIT 1
        """,
        {"cuenta_id": cuenta_id},
    )


def periodo_vigente(tipo, fecha_inicio, fecha_fin, hoy=None):
    """
    Si el periodo guardado ya venció, el presupuesto no debe quedarse
    "congelado" en la semana pasada: se recorre al periodo que contiene
    hoy (sin tocar la base). Regresa (inicio, fin, se_recorrio).
    """

    hoy = hoy or date.today()
    dias = DIAS_PERIODO.get(tipo, 30)
    inicio, fin = fecha_inicio, fecha_fin
    recorrido = False

    while fin < hoy:
        inicio = fin + timedelta(days=1)
        fin = inicio + timedelta(days=dias)
        recorrido = True

    return inicio, fin, recorrido


def obtener_estado_presupuesto(cuenta_id):
    """None si la cuenta aún no define presupuesto."""

    df = _ultimo(cuenta_id)

    if df.empty:
        return None

    fila = df.iloc[0]
    tipo = str(fila["tipo_periodo"] or "MENSUAL").upper()
    monto = float(fila["monto"] or 0)

    hoy = date.today()
    inicio, fin, recorrido = periodo_vigente(
        tipo, _fecha(fila["fecha_inicio"]), _fecha(fila["fecha_fin"]), hoy
    )

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
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": fin.isoformat(),
        "gastado": round(gastado, 2),
        "restante": round(monto - gastado, 2),
        "porcentaje": round(gastado / monto * 100, 1) if monto > 0 else 0.0,
        "dias_restantes": max((fin - hoy).days, 0),
        "periodo_reiniciado": recorrido,
    }


def guardar_presupuesto(usuario_id, cuenta_id, tipo_periodo, monto):
    """Crea o actualiza (igual que la web). Lanza ValueError si es inválido."""

    tipo = str(tipo_periodo or "").upper()

    if tipo not in DIAS_PERIODO:
        raise ValueError("Periodo inválido (SEMANAL, QUINCENAL o MENSUAL).")

    try:
        monto = round(float(monto), 2)
    except (TypeError, ValueError):
        raise ValueError("Monto inválido.")

    if not (0 <= monto <= MONTO_MAXIMO):
        raise ValueError("Monto fuera de rango.")

    inicio = date.today()
    fin = inicio + timedelta(days=DIAS_PERIODO[tipo])

    df = _ultimo(cuenta_id)

    if df.empty:
        ejecutar_query(
            """
            INSERT INTO gastos.presupuestos
                (usuario_id, cuenta_id, tipo_periodo, monto,
                 fecha_inicio, fecha_fin)
            VALUES
                (:usuario_id, :cuenta_id, :tipo, :monto, :inicio, :fin)
            """,
            {"usuario_id": usuario_id, "cuenta_id": cuenta_id,
             "tipo": tipo, "monto": monto, "inicio": inicio, "fin": fin},
        )
    else:
        ejecutar_query(
            """
            UPDATE gastos.presupuestos
            SET tipo_periodo = :tipo, monto = :monto,
                fecha_inicio = :inicio, fecha_fin = :fin
            WHERE id = :id AND cuenta_id = :cuenta_id
            """,
            {"id": int(df.iloc[0]["id"]), "cuenta_id": cuenta_id,
             "tipo": tipo, "monto": monto, "inicio": inicio, "fin": fin},
        )

    return obtener_estado_presupuesto(cuenta_id)
