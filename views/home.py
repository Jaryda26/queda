import streamlit as st
from datetime import date

from db import obtener_dataframe
from db import ejecutar_query


def registrar_pago(uid, descripcion, monto):

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
            "uid": uid,
            "concepto": descripcion,
            "monto": monto,
            "texto": f"Pago automático de {descripcion}"
        }
    )


def pantalla_home():

    uid = st.session_state["user_id"]

    hoy = date.today()

    st.title(
        f"🔔 Buenos días {st.session_state['nombre']}"
    )

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
        AND pagado = FALSE
        ORDER BY dia_vencimiento
        """
    )

    encontrados = 0

    for _, row in df.iterrows():

        dias_restantes = (
            int(row["dia_vencimiento"]) - hoy.day
        )

        if dias_restantes < 0:
            dias_restantes += 30

        if dias_restantes > int(
            row["dias_anticipacion"]
        ):
            continue

        encontrados += 1

        nivel = "🔔"

        if dias_restantes <= 1:
            nivel = "🔴"
        elif dias_restantes <= 3:
            nivel = "🟡"

        st.markdown(
            f"""
### {nivel} {row['descripcion']}

💰 **Monto:** ${float(row['monto']):,.2f}

📅 **Vence en:** {dias_restantes} día(s)
"""
        )

        c1, c2, c3 = st.columns([1, 1, 8])

        with c1:

            if st.button(
                "✅ Pagado",
                key=f"pagado_{row['id']}"
            ):

                registrar_pago(
                    uid,
                    row["descripcion"],
                    float(row["monto"])
                )

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

                st.success(
                    f"""
✅ Registré el pago de:

{row['descripcion']}

💰 ${float(row['monto']):,.2f}
"""
                )

                st.rerun()

        with c2:

            if st.button(
                "⏰ Después",
                key=f"despues_{row['id']}"
            ):

                st.info(
                    "Te lo recordaré nuevamente."
                )

        st.markdown("---")

    if encontrados == 0:

        st.success(
            "✅ No tienes recordatorios pendientes."
        )

    if st.button("Entendido"):

        st.session_state["pagina_actual"] = (
            "Dashboard"
        )

        st.rerun()