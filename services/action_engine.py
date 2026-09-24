import streamlit as st
from datetime import datetime

from db import ejecutar_query
from db import obtener_dataframe
from services.recordatorios_service import (
    marcar_pagado,
    puede_agregar_recordatorio
)


def _resolver_fecha_movimiento(resultado):
    """
    Si el usuario mencionó cuándo pasó el gasto/ingreso ("ayer",
    "antier", "el 20 de septiembre"), la IA ya lo resolvió a
    YYYY-MM-DD y llega en resultado["fecha"]. Si no vino, se usa
    el momento actual (mismo comportamiento de siempre).

    Regresa (fecha_a_usar, aviso_o_None) — nunca bloquea el
    registro: si la fecha viene mal formada, cae a hoy y avisa.
    """

    fecha_texto = resultado.get("fecha")

    if not fecha_texto:
        return datetime.now(), None

    try:

        fecha_parseada = datetime.strptime(
            str(fecha_texto),
            "%Y-%m-%d"
        ).date()

        return (
            datetime.combine(fecha_parseada, datetime.min.time()),
            None
        )

    except ValueError:

        return (
            datetime.now(),
            " (no logré interpretar la fecha que mencionaste, "
            "se guardó con la fecha de hoy)"
        )


def ejecutar_accion(resultado):

    accion = resultado.get(
        "accion",
        ""
    ).upper()

    # =====================================
    # ABRIR INICIO
    # =====================================

    if accion == "ABRIR_INICIO":

        st.session_state["pagina_actual"] = (
            "🏠 Inicio"
        )

        st.session_state[
            "debug_accion"
        ] = "inicio"

        st.rerun()

    # =====================================
    # ABRIR DASHBOARD
    # =====================================

    if accion == "ABRIR_DASHBOARD":

        st.session_state["pagina_actual"] = (
            "Dashboard"
        )

        st.session_state[
            "debug_accion"
        ] = "dashboard"

        st.rerun()

    # =====================================
    # ABRIR RECORDATORIOS
    # =====================================

    if accion == "ABRIR_RECORDATORIOS":

        st.session_state["pagina_actual"] = (
            "Recordatorios"
        )

        st.session_state[
            "debug_accion"
        ] = "recordatorios"

        st.rerun()

    # =====================================
    # ABRIR MOVIMIENTOS
    # =====================================
    if accion == "ABRIR_MOVIMIENTOS":

        st.session_state["pagina_actual"] = (
            "Movimientos"
        )

        st.session_state[
            "debug_accion"
        ] = "movimientos"

        st.rerun()

    # =====================================
    # ABRIR HISTORIAL
    # =====================================
    if accion == "ABRIR_HISTORIAL":

        st.session_state["pagina_actual"] = (
            "Historial"
        )

        st.session_state[
            "debug_accion"
        ] = "historial"

        st.rerun()

    # =====================================
    # ABRIR PRESUPUESTO
    # =====================================
    if accion == "ABRIR_PRESUPUESTO":

        st.session_state["pagina_actual"] = (
            "Presupuesto"
        )

        st.session_state[
            "debug_accion"
        ] = "presupuesto"

        st.rerun()

    # =====================================
    # ABRIR APRENDIZAJE
    # =====================================
    if accion == "ABRIR_APRENDIZAJE":

        st.session_state["pagina_actual"] = (
            "🧠 Aprendizaje"
        )

        st.session_state[
            "debug_accion"
        ] = "aprendizaje"

        st.rerun()

    # =====================================
    # ABRIR ASISTENTE
    # =====================================
    if accion == "ABRIR_ASISTENTE":

        st.session_state["pagina_actual"] = (
            "Asistente IA"
        )

        st.session_state[
            "debug_accion"
        ] = "asistente"

        st.rerun()

    # =====================================
    # ABRIR CUENTA
    # =====================================
    if accion == "ABRIR_CUENTA":

        st.session_state["pagina_actual"] = (
            "👨‍👩‍👧 Cuenta"
        )

        st.session_state[
            "debug_accion"
        ] = "cuenta"

        st.rerun()

    # =====================================
    # ABRIR SUSCRIPCIÓN
    # =====================================
    if accion == "ABRIR_SUSCRIPCION":

        st.session_state["pagina_actual"] = (
            "💳 Suscripción"
        )

        st.session_state[
            "debug_accion"
        ] = "suscripcion"

        st.rerun()
        
    # =====================================
    # PREGUNTAR MONTO INGRESO
    # =====================================

    if accion == "PREGUNTAR_MONTO_INGRESO":

        st.session_state[
            "esperando_monto_ingreso"
        ] = True

        return (
            "💰 Detecté un ingreso.\n\n"
            "¿Cuál fue el monto?"
        )

    # =====================================
    # POSPONER RECORDATORIO
    # =====================================

    if accion == "POSPONER_RECORDATORIO":

        descripcion = resultado.get(
            "descripcion",
            ""
        )

        recordatorios = obtener_dataframe(
            """
            SELECT *
            FROM gastos.recordatorios
            WHERE cuenta_id = :cuenta_id
            AND pagado = FALSE
            """,
            {"cuenta_id": st.session_state["cuenta_id"]}
        )

        if recordatorios.empty:

            return (
                "⚠ No existen recordatorios pendientes."
            )

        coincidencia = recordatorios[
            recordatorios["descripcion"]
            .str.upper()
            .str.contains(
                descripcion.upper(),
                na=False
            )
        ]

        if coincidencia.empty:

            return (
                f"⚠ No encontré {descripcion}"
            )

        row = coincidencia.iloc[0]

        ejecutar_query(
            """
            UPDATE gastos.recordatorios
            SET
                fecha_proxima_alerta =
                CURRENT_DATE + INTERVAL '1 day'
            WHERE id = :id
            """,
            {
                "id": int(row["id"])
            }
        )

        return (
            f"⏰ Te recordaré mañana: "
            f"{row['descripcion']}"
        )

    # =====================================
    # PAGAR RECORDATORIO
    # =====================================

    if accion == "PAGAR_RECORDATORIO":

        descripcion = resultado.get(
            "descripcion",
            ""
        )

        recordatorios = obtener_dataframe(
            """
            SELECT *
            FROM gastos.recordatorios
            WHERE cuenta_id = :cuenta_id
            AND pagado = FALSE
            """,
            {"cuenta_id": st.session_state["cuenta_id"]}
        )

        if recordatorios.empty:

            return (
                "⚠ No existen recordatorios pendientes."
            )

        coincidencia = recordatorios[
            recordatorios["descripcion"]
            .str.upper()
            .str.contains(
                descripcion.upper(),
                na=False
            )
        ]

        if coincidencia.empty:

            return (
                f"⚠ No encontré {descripcion}"
            )

        row = coincidencia.iloc[0]

        marcar_pagado(
            int(row["id"]),
            row["fecha_vencimiento"],
            row["frecuencia"]
        )

        ejecutar_query(
            """
            INSERT INTO gastos.movimientos
            (
                usuario_id,
                cuenta_id,
                tipo,
                categoria,
                concepto,
                monto,
                texto_original
            )
            VALUES
            (
                :uid,
                :cuenta_id,
                'GASTO',
                'Recordatorio',
                :concepto,
                :monto,
                :texto
            )
            """,
            {
                "uid":
                    st.session_state["user_id"],

                "cuenta_id":
                    st.session_state["cuenta_id"],

                "concepto":
                    row["descripcion"],

                "monto":
                    float(row["monto"]),

                "texto":
                    f"Pago automático de {row['descripcion']}"
            }
        )

        if str(row["frecuencia"]).upper() == "UNICO":

            return (
                f"✅ Marqué como pagado "
                f"{row['descripcion']}"
            )

        return (
            f"✅ Registré el pago de "
            f"{row['descripcion']}.\n\n"
            f"Seguirá activo por ser "
            f"{row['frecuencia']}."
        )

    # =====================================
    # REGISTRAR GASTO
    # =====================================

    if accion == "REGISTRAR_GASTO":

        monto = float(
            resultado.get(
                "monto",
                0
            )
        )

        if monto <= 0:

            return (
                "⚠ No pude identificar "
                "el importe del gasto."
            )

        fecha_movimiento, aviso_fecha = _resolver_fecha_movimiento(
            resultado
        )

        ejecutar_query(
            """
            INSERT INTO gastos.movimientos
            (
                usuario_id,
                cuenta_id,
                tipo,
                categoria,
                concepto,
                monto,
                texto_original,
                fecha
            )
            VALUES
            (
                :uid,
                :cuenta_id,
                'GASTO',
                :categoria,
                :concepto,
                :monto,
                :texto,
                :fecha
            )
            """,
            {
                "uid":
                    st.session_state["user_id"],

                "cuenta_id":
                    st.session_state["cuenta_id"],

                "categoria":
                    resultado.get(
                        "categoria",
                        "Otros"
                    ),

                "concepto":
                    resultado.get(
                        "concepto",
                        "Gasto"
                    ),

                "monto":
                    monto,

                "texto":
                    resultado.get(
                        "texto_original",
                        ""
                    ),

                "fecha":
                    fecha_movimiento
            }
        )

        return (
            f"✅ Gasto registrado "
            f"${monto:,.2f}"
            f"{f' el {fecha_movimiento:%d/%m/%Y}' if resultado.get('fecha') else ''}"
            f"{aviso_fecha or ''}"
        )

    # =====================================
    # REGISTRAR INGRESO
    # =====================================

    if accion == "REGISTRAR_INGRESO":

        monto = float(
            resultado.get(
                "monto",
                0
            )
        )

        if monto <= 0:

            return (
                "⚠ No pude identificar "
                "el importe del ingreso."
            )

        fecha_movimiento, aviso_fecha = _resolver_fecha_movimiento(
            resultado
        )

        ejecutar_query(
            """
            INSERT INTO gastos.movimientos
            (
                usuario_id,
                cuenta_id,
                tipo,
                categoria,
                concepto,
                monto,
                texto_original,
                origen_ingreso,
                fecha
            )
            VALUES
            (
                :uid,
                :cuenta_id,
                'INGRESO',
                'Ingreso',
                :concepto,
                :monto,
                :texto,
                :origen,
                :fecha
            )
            """,
            {
                "uid":
                    st.session_state["user_id"],

                "cuenta_id":
                    st.session_state["cuenta_id"],

                "concepto":
                    resultado.get(
                        "concepto",
                        "Ingreso"
                    ),

                "monto":
                    monto,

                "texto":
                    resultado.get(
                        "texto_original",
                        ""
                    ),

                "origen":
                    resultado.get(
                        "origen_ingreso",
                        "Otro"
                    ),

                "fecha":
                    fecha_movimiento
            }
        )

        return (
            f"✅ Ingreso registrado "
            f"${monto:,.2f}"
            f"{f' el {fecha_movimiento:%d/%m/%Y}' if resultado.get('fecha') else ''}"
            f"{aviso_fecha or ''}"
        )

    # =====================================
    # CREAR RECORDATORIO (por voz o texto)
    # =====================================

    if accion == "CREAR_RECORDATORIO":

        cuenta_id = st.session_state["cuenta_id"]

        descripcion = str(
            resultado.get("descripcion", "")
        ).strip()

        monto = float(
            resultado.get("monto", 0) or 0
        )

        fecha_vencimiento = resultado.get(
            "fecha_vencimiento"
        )

        frecuencia = str(
            resultado.get("frecuencia", "UNICO")
        ).upper()

        if frecuencia not in (
            "UNICO", "SEMANAL", "QUINCENAL", "MENSUAL", "ANUAL"
        ):
            frecuencia = "UNICO"

        dias_anticipacion = int(
            resultado.get("dias_anticipacion", 3) or 3
        )

        if not descripcion or not fecha_vencimiento:

            return (
                "⚠ No pude identificar bien la descripción o la "
                "fecha del recordatorio. Intenta de nuevo siendo "
                "más específico, por ejemplo: 'recuérdame pagar "
                "la tarjeta Sears el 30 de este mes por 1300 "
                "pesos'."
            )

        try:

            fecha_vencimiento = datetime.strptime(
                str(fecha_vencimiento),
                "%Y-%m-%d"
            ).date()

        except ValueError:

            return (
                "⚠ No logré entender bien la fecha. Intenta "
                "decirla de forma más clara, por ejemplo "
                "'el 30 de este mes' o 'el próximo viernes'."
            )

        puede, mensaje_limite = puede_agregar_recordatorio(
            cuenta_id
        )

        if not puede:
            return f"⚠ {mensaje_limite}"

        ejecutar_query(
            """
            INSERT INTO gastos.recordatorios
            (
                usuario_id,
                cuenta_id,
                descripcion,
                monto,
                fecha_vencimiento,
                dias_anticipacion,
                frecuencia
            )
            VALUES
            (
                :uid,
                :cuenta_id,
                :descripcion,
                :monto,
                :fecha_vencimiento,
                :dias,
                :frecuencia
            )
            """,
            {
                "uid": st.session_state["user_id"],
                "cuenta_id": cuenta_id,
                "descripcion": descripcion,
                "monto": monto,
                "fecha_vencimiento": fecha_vencimiento,
                "dias": dias_anticipacion,
                "frecuencia": frecuencia
            }
        )

        return (
            f"🔔 Recordatorio creado: {descripcion} "
            f"(${monto:,.2f}), vence {fecha_vencimiento}."
        )

    return "⚠ Acción no reconocida"