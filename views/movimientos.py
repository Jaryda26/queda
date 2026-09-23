import streamlit as st
from db import ejecutar_query


def pantalla_movimientos():

    st.title("💳 Movimientos")

    uid = st.session_state["user_id"]

    tipo = st.selectbox(
        "Tipo",
        ["INGRESO", "GASTO"]
    )

    categoria = st.selectbox(
        "Categoría",
        [
            "Gasolina",
            "Comida",
            "Servicios",
            "Transporte",
            "Salud",
            "Entretenimiento",
            "Otros"
        ]
    )

    concepto = st.text_input("Concepto")

    monto = st.number_input(
        "Monto",
        min_value=0.0
    )

    if st.button("Guardar Movimiento"):

        if not concepto.strip() or monto <= 0:

            st.warning(
                "Escribe un concepto y un monto mayor a 0."
            )

        else:

            ejecutar_query(
                """
                INSERT INTO gastos.movimientos
                (usuario_id, tipo, categoria, concepto, monto)
                VALUES (:u, :t, :cat, :c, :m)
                """,
                {
                    "u": uid,
                    "t": tipo,
                    "cat": categoria,
                    "c": concepto.strip(),
                    "m": monto
                }
            )

            st.success("✅ Movimiento guardado")
            st.rerun()
