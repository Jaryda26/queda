import streamlit as st

from db import ejecutar_query
from db import obtener_dataframe


def ejecutar_accion(resultado):

    accion = resultado.get("accion", "").upper()

    if accion == "ABRIR_DASHBOARD":

        st.session_state["pagina_actual"] = "Dashboard"

        return "📊 Abriendo Dashboard"

    if accion == "ABRIR_RECORDATORIOS":

        st.session_state["pagina_actual"] = "Recordatorios"

        return "🔔 Abriendo Recordatorios"

    if accion == "REGISTRAR_GASTO":

        monto = float(
            resultado.get("monto", 0)
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
                :tipo,
                :categoria,
                :concepto,
                :monto,
                :texto_original
            )
            """,
            {
                "uid": st.session_state["user_id"],
                "tipo": "GASTO",
                "categoria": resultado.get(
                    "categoria",
                    "Otros"
                ),
                "concepto": resultado.get(
                    "concepto",
                    "Gasto"
                ),
                "monto": monto,
                "texto_original": resultado.get(
                    "texto_original",
                    ""
                )
            }
        )

        return f"✅ Gasto registrado por ${monto:,.2f}"

    if accion == "REGISTRAR_INGRESO":

        monto = float(
            resultado.get("monto", 0)
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
                :tipo,
                :categoria,
                :concepto,
                :monto,
                :texto_original,
                :origen_ingreso
            )
            """,
            {
                "uid": st.session_state["user_id"],
                "tipo": "INGRESO",
                "categoria": "Ingreso",
                "concepto": resultado.get(
                    "concepto",
                    "Ingreso"
                ),
                "monto": monto,
                "texto_original": resultado.get(
                    "texto_original",
                    ""
                ),
                "origen_ingreso": resultado.get(
                    "origen_ingreso",
                    "Otro"
                )
            }
        )

        return f"✅ Ingreso registrado por ${monto:,.2f}"

    if accion == "PAGAR_RECORDATORIO":

        descripcion = resultado.get(
            "descripcion",
            ""
        )

        sql = """
        SELECT
            id,
            descripcion,
            monto
        FROM gastos.recordatorios
        WHERE usuario_id = :uid
        AND pagado = FALSE
        """

        recordatorios = obtener_dataframe(
            sql.replace(
                ":uid",
                str(st.session_state["user_id"])
            )
        )

        if recordatorios.empty:

            return (
                "⚠ No existen "
                "recordatorios pendientes."
            )

        coincidencia = recordatorios[
            recordatorios[
                "descripcion"
            ].str.upper().str.contains(
                descripcion.upper(),
                na=False
            )
        ]

        if coincidencia.empty:

            return (
                "⚠ No encontré "
                f"{descripcion}"
            )

        row = coincidencia.iloc[0]

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
                :texto_original
            )
            """,
            {
                "uid": st.session_state["user_id"],
                "concepto": row["descripcion"],
                "monto": float(row["monto"]),
                "texto_original":
                    f"Pago automático de {row['descripcion']}"
            }
        )

        return (
            f"✅ Marqué como pagado "
            f"{row['descripcion']}"
        )

    return "⚠ Acción no reconocida"