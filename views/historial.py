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

            texto_detalle = (
                f"**Tipo:** {row['tipo']}\n\n"
                f"**Categoría:** {row['categoria']}\n\n"
                f"**Concepto:** {row['concepto']}\n\n"
                f"**Monto:** ${float(row['monto']):,.2f}\n\n"
            )

            # "Origen ingreso" solo aplica a movimientos tipo
            # INGRESO — en un GASTO esa columna siempre está vacía
            # en la base, y mostrarla igual salía como "nan"
            # (así se ve un NULL de Postgres una vez que pandas
            # lo trae), que no significa nada para el usuario.

            if (
                row["tipo"] == "INGRESO"
                and pd.notna(row["origen_ingreso"])
                and str(row["origen_ingreso"]).strip()
            ):

                texto_detalle += (
                    f"**Origen ingreso:** "
                    f"{row['origen_ingreso']}\n\n"
                )

            if (
                pd.notna(row["texto_original"])
                and str(row["texto_original"]).strip()
            ):

                texto_detalle += (
                    f"**Texto original:** "
                    f"{row['texto_original']}\n\n"
                )

            st.markdown(texto_detalle)

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