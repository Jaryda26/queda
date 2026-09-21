import streamlit as st
from datetime import date

from db import ejecutar_query
from db import obtener_dataframe


def pantalla_recordatorios():

    uid = st.session_state["user_id"]

    st.title("🔔 Recordatorios")

    st.subheader("Nuevo Recordatorio")

    descripcion = st.text_input(
        "Descripción"
    )

    monto = st.number_input(
        "Monto",
        min_value=0.0,
        step=100.0
    )

    fecha_vencimiento = st.date_input(
        "Fecha de vencimiento",
        value=date.today()
    )

    dias_anticipacion = st.selectbox(
        "Avisar con",
        [7, 3, 1]
    )

    frecuencia = st.selectbox(
        "Frecuencia",
        [
            "UNICO",
            "SEMANAL",
            "QUINCENAL",
            "MENSUAL",
            "ANUAL"
        ]
    )

    if st.button(
        "Guardar Recordatorio"
    ):

        ejecutar_query(
            """
            INSERT INTO gastos.recordatorios
            (
                usuario_id,
                descripcion,
                monto,
                fecha_vencimiento,
                dias_anticipacion,
                frecuencia
            )
            VALUES
            (
                :uid,
                :descripcion,
                :monto,
                :fecha_vencimiento,
                :dias,
                :frecuencia
            )
            """,
            {
                "uid": uid,
                "descripcion": descripcion,
                "monto": monto,
                "fecha_vencimiento": fecha_vencimiento,
                "dias": dias_anticipacion,
                "frecuencia": frecuencia
            }
        )

        st.success(
            "✅ Recordatorio guardado"
        )

        st.rerun()

    st.markdown("---")

    st.subheader(
        "Recordatorios configurados"
    )

    df = obtener_dataframe(
        f"""
        SELECT
            id,
            descripcion,
            monto,
            fecha_vencimiento,
            dias_anticipacion,
            frecuencia,
            pagado,
            fecha_ultimo_pago
        FROM gastos.recordatorios
        WHERE usuario_id = {uid}
        ORDER BY fecha_vencimiento
        """
    )

    if df.empty:

        st.info(
            "No existen recordatorios."
        )

        return

    for _, row in df.iterrows():

        estado = (
            "✅ PAGADO"
            if row["pagado"]
            else "🔔 PENDIENTE"
        )

        with st.expander(
            f"{row['descripcion']} - {estado}"
        ):

            nueva_descripcion = st.text_input(
                "Descripción",
                value=row["descripcion"],
                key=f"desc_{row['id']}"
            )

            nuevo_monto = st.number_input(
                "Monto",
                min_value=0.0,
                value=float(row["monto"]),
                key=f"monto_{row['id']}"
            )

            nueva_fecha = st.date_input(
                "Fecha vencimiento",
                value=row["fecha_vencimiento"],
                key=f"fecha_{row['id']}"
            )

            nueva_anticipacion = st.selectbox(
                "Avisar con",
                [7, 3, 1],
                index=[7, 3, 1].index(
                    int(row["dias_anticipacion"])
                ),
                key=f"anti_{row['id']}"
            )

            frecuencias = [
                "UNICO",
                "SEMANAL",
                "QUINCENAL",
                "MENSUAL",
                "ANUAL"
            ]

            nueva_frecuencia = st.selectbox(
                "Frecuencia",
                frecuencias,
                index=(
                    frecuencias.index(
                        str(row["frecuencia"])
                    )
                    if str(row["frecuencia"]) in frecuencias
                    else 3
                ),
                key=f"freq_{row['id']}"
            )

            c1, c2, c3 = st.columns(3)

            with c1:

                if st.button(
                    "💾 Guardar",
                    key=f"save_{row['id']}"
                ):

                    ejecutar_query(
                        """
                        UPDATE gastos.recordatorios
                        SET
                            descripcion = :descripcion,
                            monto = :monto,
                            fecha_vencimiento = :fecha,
                            dias_anticipacion = :anticipacion,
                            frecuencia = :frecuencia
                        WHERE id = :id
                        """,
                        {
                            "descripcion": nueva_descripcion,
                            "monto": nuevo_monto,
                            "fecha": nueva_fecha,
                            "anticipacion": nueva_anticipacion,
                            "frecuencia": nueva_frecuencia,
                            "id": int(row["id"])
                        }
                    )

                    st.success(
                        "✅ Actualizado"
                    )

                    st.rerun()

            with c2:

                if not row["pagado"]:

                    if st.button(
                        "✅ Pagar",
                        key=f"pay_{row['id']}"
                    ):

                        if (
                            str(row["frecuencia"]).upper()
                            == "UNICO"
                        ):

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

                        st.success(
                            "✅ Pago registrado"
                        )

                        st.rerun()

                else:

                    if (
                        str(row["frecuencia"]).upper()
                        == "UNICO"
                    ):

                        if st.button(
                            "↩ Reabrir",
                            key=f"open_{row['id']}"
                        ):

                            ejecutar_query(
                                """
                                UPDATE gastos.recordatorios
                                SET pagado = FALSE
                                WHERE id = :id
                                """,
                                {
                                    "id": int(row["id"])
                                }
                            )

                            st.rerun()

                    else:

                        st.success(
                            f"""
✅ Pago recurrente

Frecuencia:
{row['frecuencia']}

Seguirá activo para el siguiente periodo.
"""
                        )

            with c3:

                if st.button(
                    "🗑 Eliminar",
                    key=f"delete_{row['id']}"
                ):

                    ejecutar_query(
                        """
                        DELETE
                        FROM gastos.recordatorios
                        WHERE id = :id
                        """,
                        {
                            "id": int(row["id"])
                        }
                    )

                    st.rerun()