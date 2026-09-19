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

        if dias_restantes <= 1:

            st.error(
                f"""
🔴 {row['descripcion']}

Monto: ${float(row['monto']):,.2f}

Vence mañana o hoy.
"""
            )

        elif dias_restantes <= 3:

            st.warning(
                f"""
🟡 {row['descripcion']}

Monto: ${float(row['monto']):,.2f}

Vence en {dias_restantes} días.
"""
            )

        else:

            st.info(
                f"""
🔔 {row['descripcion']}

Monto: ${float(row['monto']):,.2f}

Vence en {dias_restantes} días.
"""
            )

        c1, c2 = st.columns(2)

        with c1:

            if st.button(
                "✅ Ya lo pagué",
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
                    "Pago registrado correctamente."
                )

                st.rerun()

        with c2:

            if st.button(
                "⏰ Recordarme después",
                key=f"recordar_{row['id']}"
            ):
                st.info(
                    "Te lo volveré a mostrar."
                )

    if encontrados == 0:

        st.success(
            "✅ No tienes recordatorios pendientes."
        )

    if st.button("Entendido"):

        st.session_state["pagina_actual"] = (
            "Dashboard"
        )

        st.rerun()