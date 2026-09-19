import streamlit as st
from datetime import date

from db import obtener_dataframe


def pantalla_home():

    uid = st.session_state["user_id"]

    hoy = date.today()

    st.title(
        f"🔔 Buenos días {st.session_state['nombre']}"
    )

    df = obtener_dataframe(
        f"""
        SELECT
            descripcion,
            monto,
            dia_vencimiento,
            dias_anticipacion
        FROM gastos.recordatorios
        WHERE usuario_id = {uid}
        AND activo = TRUE
        AND pagado = FALSE
        ORDER BY dia_vencimiento
        """
    )

    recordatorios_mostrados = 0

    for _, row in df.iterrows():

        dia_vencimiento = int(
            row["dia_vencimiento"]
        )

        dias_restantes = (
            dia_vencimiento - hoy.day
        )

        if dias_restantes < 0:
            dias_restantes += 30

        if dias_restantes > int(
            row["dias_anticipacion"]
        ):
            continue

        recordatorios_mostrados += 1

        if dias_restantes <= 1:

            st.error(
                f"""
🔴 {row['descripcion']}

Monto:
${float(row['monto']):,.2f}

Vence mañana o hoy.
"""
            )

        elif dias_restantes <= 3:

            st.warning(
                f"""
🟡 {row['descripcion']}

Monto:
${float(row['monto']):,.2f}

Vence en {dias_restantes} días.
"""
            )

        else:

            st.info(
                f"""
🔔 {row['descripcion']}

Monto:
${float(row['monto']):,.2f}

Vence en {dias_restantes} días.
"""
            )

    if recordatorios_mostrados == 0:

        st.success(
            "✅ No tienes recordatorios pendientes."
        )

    if st.button("Entendido"):

        st.session_state["home_vista"] = False

        st.rerun()