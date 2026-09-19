import streamlit as st

from db import ejecutar_query
from db import obtener_dataframe


def ejecutar_accion(resultado):

    accion = resultado.get(
        "accion",
        ""
    ).upper()

    if accion == "ABRIR_DASHBOARD":

        st.session_state["pagina_actual"] = (
            "Dashboard"
        )

        return "📊 Abriendo Dashboard"

    if accion == "ABRIR_RECORDATORIOS":

        st.session_state["pagina_actual"] = (
            "Recordatorios"
        )

        return "🔔 Abriendo Recordatorios"

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
                "⚠ No encontré "
                "recordatorios pendientes."
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
                f"⚠ No encontré "
                f"{descripcion}"
            )

        row = coincidencia.iloc[0]

        return (
            f"⏰ Te recordaré después "
            f"{row['descripcion']}"
        )

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
                "⚠ No existen "
                "recordatorios pendientes."
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
                f"⚠ No encontré "
                f"{descripcion}"
            )

        row = coincidencia.iloc[0]

        ejecutar_query(
            """
            UPDATE gastos.recordatorios
            SET
                pagado = TRUE,
                fecha_ultimo_pago =
                CURRENT_DATE
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

        return (
            f"✅ Marqué como pagado "
            f"{row['descripcion']}"
        )

    if accion == "REGISTRAR_GASTO":

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
                    resultado.get(
                        "monto",
                        0
                    ),

                "texto":
                    resultado.get(
                        "texto_original",
                        ""
                    )
            }
        )

        monto = float(
            resultado.get(
                "monto",
                0
            )
        )

        return (
            f"✅ Gasto registrado "
            f"${monto:,.2f}"
        )

    if accion == "REGISTRAR_INGRESO":

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
                    resultado.get(
                        "monto",
                        0
                    ),

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

        monto = float(
            resultado.get(
                "monto",
                0
            )
        )

        return (
            f"✅ Ingreso registrado "
            f"${monto:,.2f}"
        )

    return "⚠ Acción no reconocida"