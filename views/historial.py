import streamlit as st

from db import obtener_dataframe


def pantalla_historial():

    uid = st.session_state["user_id"]

    df = obtener_dataframe(
        f"""
        SELECT
            fecha,
            categoria,
            concepto,
            tipo,
            monto,
            texto_original
        FROM gastos.movimientos
        WHERE usuario_id = {uid}
        ORDER BY fecha DESC
        """
    )

    st.title("📜 Historial")

    st.dataframe(
        df,
        use_container_width=True
    )