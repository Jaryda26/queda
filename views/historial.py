import streamlit as st
import pandas as pd

from db import obtener_dataframe
from db import ejecutar_query


def pantalla_historial():

    cuenta_id = st.session_state["cuenta_id"]

    st.title("📜 Historial")

    df = obtener_dataframe(
        """
        SELECT
            id,
            fecha,
            categoria,
            concepto,
            tipo,
            monto,
            origen_ingreso,
            texto_original
        FROM gastos.movimientos
        WHERE cuenta_id = :cuenta_id
        ORDER BY fecha DESC
        """,
        {"cuenta_id": cuenta_id}
    )

    if df.empty:

        st.info(
            "No existen movimientos."
        )

        return

    try:

        df["fecha"] = pd.to_datetime(
            df["fecha"]
        )

        # Ajuste horario local
        df["fecha"] = (
            df["fecha"]
            - pd.Timedelta(hours=6)
        )

    except Exception:
        pass

    for _, row in df.iterrows():

        with st.expander(
            f"{row['fecha']} | {row['concepto']} | ${float(row['monto']):,.2f}"
        ):

            st.markdown(
                f"""
**Tipo:** {row['tipo']}

**Categoría:** {row['categoria']}

**Concepto:** {row['concepto']}

**Monto:** ${float(row['monto']):,.2f}

**Origen ingreso:** {row['origen_ingreso']}

**Texto original:** {row['texto_original']}
"""
            )

            c1, c2 = st.columns(2)

            with c1:

                st.caption(
                    f"ID: {int(row['id'])}"
                )

            with c2:

                if st.button(
                    "🗑 Eliminar",
                    key=f"del_{row['id']}"
                ):

                    ejecutar_query(
                        """
                        DELETE
                        FROM gastos.movimientos
                        WHERE id = :id
                        """,
                        {
                            "id": int(row["id"])
                        }
                    )

                    st.success(
                        "✅ Movimiento eliminado"
                    )

                    st.rerun()