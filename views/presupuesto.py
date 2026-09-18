import streamlit as st

from datetime import date
from datetime import timedelta

from db import ejecutar_query
from db import obtener_dataframe


def pantalla_presupuesto():

    uid = st.session_state["user_id"]

    st.title("Presupuesto")

    tipo = st.selectbox(
        "Periodo",
        [
            "SEMANAL",
            "QUINCENAL",
            "MENSUAL"
        ]
    )

    monto = st.number_input(
        "Monto",
        min_value=0.0
    )

    if st.button(
        "Guardar Presupuesto"
    ):

        dias = {
            "SEMANAL": 7,
            "QUINCENAL": 15,
            "MENSUAL": 30
        }

        fecha_inicio = date.today()

        fecha_fin = fecha_inicio + timedelta(
            days=dias[tipo]
        )

        ejecutar_query(
            """
            INSERT INTO gastos.presupuestos
            (
                usuario_id,
                tipo_periodo,
                monto,
                fecha_inicio,
                fecha_fin
            )
            VALUES
            (
                :usuario_id,
                :tipo_periodo,
                :monto,
                :fecha_inicio,
                :fecha_fin
            )
            """,
            {
                "usuario_id": uid,
                "tipo_periodo": tipo,
                "monto": monto,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin
            }
        )

        st.success(
            "Presupuesto guardado"
        )

    df = obtener_dataframe(
        f"""
        SELECT *
        FROM gastos.presupuestos
        WHERE usuario_id = {uid}
        ORDER BY id DESC
        LIMIT 10
        """
    )

    st.dataframe(
        df,
        use_container_width=True
    )