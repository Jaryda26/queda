import streamlit as st

from db import ejecutar_query
from db import obtener_dataframe


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

        st.rerun()

    # =====================================
    # ABRIR DASHBOARD
    # =====================================

    if accion == "ABRIR_DASHBOARD":

        st.session_state["pagina_actual"] = (
            "Dashboard"
        )

        st.session_state["debug_accion"] = (
            "dashboard"
        )

        st.rerun()

    # =====================================
    # ABRIR RECORDATORIOS
    # =====================================

    if accion == "ABRIR_RECORDATORIOS":

        st.session_state["pagina_actual"] = (
            "Recordatorios"
        )

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
            f"""
            SELECT *
            FROM gastos.recordatorios
            WHERE usuario_id =
            {st.session_state["user_id"]}
            AND pagado = FALSE
            """
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
            f"""
            SELECT *
            FROM gastos.recordatorios
            WHERE usuario_id =
            {st.session_state["user_id"]}
            AND pagado = FALSE
            """
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

        frecuencia = str(
            row["frecuencia"]
        ).upper()

        if frecuencia == "UNICO":

            ejecutar_query(
                """
                UPDATE gastos.recordatorios
                SET
                    pagado = TRUE,
                    fecha_ultimo_pago = CURRENT_DATE
                WHERE id = :id
                """,
                {
                    "id": int(row["id"])
                }
            )

        else:

            ejecutar_query(
                """
                UPDATE gastos.recordatorios
                SET
                    fecha_ultimo_pago = CURRENT_DATE
                WHERE id = :id
                """,
                {
                    "id": int(row["id"])
                }
            )

        ejecutar_query(
            """
            INSERT INTO gastos.movimientos
            (
                usuario_id,
                tipo,
                categoria,
                concepto,
                monto,
                texto_original
            )
            VALUES
            (
                :uid,
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

                "concepto":
                    row["descripcion"],

                "monto":
                    float(row["monto"]),

                "texto":
                    f"Pago automático de {row['descripcion']}"
            }
        )

        if frecuencia == "UNICO":

            return (
                f"✅ Marqué como pagado "
                f"{row['descripcion']}"
            )

        return (
            f"✅ Registré el pago de "
            f"{row['descripcion']}.\n\n"
            f"Seguirá activo por ser "
            f"{frecuencia}."
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

        ejecutar_query(
            """
            INSERT INTO gastos.movimientos
            (
                usuario_id,
                tipo,
                categoria,
                concepto,
                monto,
                texto_original
            )
            VALUES
            (
                :uid,
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

        ejecutar_query(
            """
            INSERT INTO gastos.movimientos
            (
                usuario_id,
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