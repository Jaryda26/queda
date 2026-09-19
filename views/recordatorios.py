import streamlit as st

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
                "dia": dia_vencimiento,
                "anticipacion": dias_anticipacion
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

        estado = (
            "✅ PAGADO"
            if row["pagado"]
            else "🔔 PENDIENTE"
        )

        with st.expander(
            f"{row['descripcion']} - {estado}"
        ):

            nuevo_descripcion = st.text_input(
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

            nuevo_dia = st.selectbox(
                "Día vencimiento",
                list(range(1, 32)),
                index=int(row["dia_vencimiento"]) - 1,
                key=f"dia_{row['id']}"
            )

            nueva_anticipacion = st.selectbox(
                "Avisar con",
                [7, 3, 1],
                index=[7, 3, 1].index(
                    int(row["dias_anticipacion"])
                )
                if int(row["dias_anticipacion"]) in [7, 3, 1]
                else 0,
                key=f"anti_{row['id']}"
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
                            descripcion=:descripcion,
                            monto=:monto,
                            dia_vencimiento=:dia,
                            dias_anticipacion=:anticipacion
                        WHERE id=:id
                        """,
                        {
                            "descripcion":
                                nuevo_descripcion,
                            "monto":
                                nuevo_monto,
                            "dia":
                                nuevo_dia,
                            "anticipacion":
                                nueva_anticipacion,
                            "id":
                                int(row["id"])
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

                        ejecutar_query(
                            """
                            UPDATE gastos.recordatorios
                            SET
                                pagado=TRUE,
                                fecha_ultimo_pago=CURRENT_DATE
                            WHERE id=:id
                            """,
                            {
                                "id":
                                    int(row["id"])
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
                            SET pagado=FALSE
                            WHERE id=:id
                            """,
                            {
                                "id":
                                    int(row["id"])
                            }
                        )

                        st.rerun()

            with c3:

                if st.button(
                    "🗑 Eliminar",
                    key=f"delete_{row['id']}"
                ):

                    ejecutar_query(
                        """
                        DELETE
                        FROM gastos.recordatorios
                        WHERE id=:id
                        """,
                        {
                            "id":
                                int(row["id"])
                        }
                    )

                    st.rerun()