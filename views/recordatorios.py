import streamlit as st

from db import ejecutar_query
from db import obtener_dataframe


def pantalla_recordatorios():

    uid = st.session_state["user_id"]

    st.title("🔔 Recordatorios")

    st.markdown(
        """
Configura pagos recurrentes como:

- Tarjeta BBVA
- Netflix
- Seguro Auto
- Internet
- Colegiaturas
"""
    )

    descripcion = st.text_input(
        "Descripción"
    )

    monto = st.number_input(
        "Monto",
        min_value=0.0,
        step=100.0
    )

    dia_vencimiento = st.selectbox(
        "Día de vencimiento",
        list(range(1, 32))
    )

    dias_anticipacion = st.selectbox(
        "Avisar con",
        [7, 3, 1]
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
                dia_vencimiento,
                dias_anticipacion
            )
            VALUES
            (
                :usuario_id,
                :descripcion,
                :monto,
                :dia_vencimiento,
                :dias_anticipacion
            )
            """,
            {
                "usuario_id": uid,
                "descripcion": descripcion,
                "monto": monto,
                "dia_vencimiento": dia_vencimiento,
                "dias_anticipacion": dias_anticipacion
            }
        )

        st.success(
            "✅ Recordatorio guardado"
        )

        st.rerun()

    st.markdown("---")

    st.subheader("Recordatorios activos")

    df = obtener_dataframe(
        f"""
        SELECT
            id,
            descripcion,
            monto,
            dia_vencimiento,
            dias_anticipacion,
            pagado
        FROM gastos.recordatorios
        WHERE usuario_id = {uid}
        ORDER BY id DESC
        """
    )

    if df.empty:

        st.info(
            "No existen recordatorios."
        )

        return

    for _, row in df.iterrows():

        col1, col2 = st.columns([4, 1])

        with col1:

            estado = (
                "✅ Pagado"
                if row["pagado"]
                else "🔔 Pendiente"
            )

            st.markdown(
                f"""
**{row['descripcion']}**

Monto: ${float(row['monto']):,.2f}

Vence día: {row['dia_vencimiento']}

Avisar: {row['dias_anticipacion']} días antes

Estado: {estado}
"""
            )

        with col2:

            if not row["pagado"]:

                if st.button(
                    "✅ Pagar",
                    key=f"pay_{row['id']}"
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

                    st.rerun()

            else:

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