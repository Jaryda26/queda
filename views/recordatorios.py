import streamlit as st

from db import ejecutar_query
from db import obtener_dataframe


def pantalla_recordatorios():

    uid = st.session_state["user_id"]

    st.title("🔔 Recordatorios")

    descripcion = st.text_input(
        "Descripción"
    )

    monto = st.number_input(
        "Monto",
        min_value=0.0
    )

    dia = st.selectbox(
        "Día de vencimiento",
        list(range(1, 32))
    )

    anticipacion = st.selectbox(
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
                :uid,
                :descripcion,
                :monto,
                :dia,
                :anticipacion
            )
            """,
            {
                "uid": uid,
                "descripcion": descripcion,
                "monto": monto,
                "dia": dia,
                "anticipacion": anticipacion
            }
        )

        st.success(
            "✅ Recordatorio guardado"
        )

    df = obtener_dataframe(
        f"""
        SELECT *
        FROM gastos.recordatorios
        WHERE usuario_id = {uid}
        ORDER BY id DESC
        """
    )

    st.dataframe(
        df,
        use_container_width=True
    )