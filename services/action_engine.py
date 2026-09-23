import streamlit as st

from db import ejecutar_query
from db import obtener_dataframe
from services.recordatorios_service import marcar_pagado


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
                :categoria,
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
                    )
            }
        )

        return (
            f"✅ Gasto registrado "
            f"${monto:,.2f}"
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
                origen_ingreso
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
                :origen
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
                    )
            }
        )

        return (
            f"✅ Ingreso registrado "
            f"${monto:,.2f}"
        )

    return "⚠ Acción no reconocida"