import streamlit as st

from datetime import date
from datetime import timedelta

from db import ejecutar_query
from db import obtener_dataframe


def pantalla_presupuesto():

    uid = st.session_state["user_id"]

    st.title("🎯 Presupuesto")

    presupuesto_actual = obtener_dataframe(
        """
        SELECT *
        FROM gastos.presupuestos
        WHERE usuario_id = :uid
        ORDER BY id DESC
        LIMIT 1
        """,
        {"uid": uid}
    )

    monto_default = 0.0
    tipo_default = "MENSUAL"

    if not presupuesto_actual.empty:

        monto_default = float(
            presupuesto_actual.iloc[0]["monto"]
        )

        tipo_default = str(
            presupuesto_actual.iloc[0]["tipo_periodo"]
        )

        st.info(
            f"""
✅ Presupuesto actual encontrado

Periodo actual: {tipo_default}

Monto actual: ${monto_default:,.2f}

Modifica los valores y presiona
"Actualizar Presupuesto".
"""
        )

    opciones = [
        "SEMANAL",
        "QUINCENAL",
        "MENSUAL"
    ]

    indice = 0

    if tipo_default in opciones:
        indice = opciones.index(tipo_default)

    tipo = st.selectbox(
        "Periodo",
        opciones,
        index=indice
    )

    monto = st.number_input(
        "Monto",
        min_value=0.0,
        value=monto_default
    )

    texto_boton = (
        "Crear Presupuesto"
        if presupuesto_actual.empty
        else "Actualizar Presupuesto"
    )

    if st.button(texto_boton):

        dias = {
            "SEMANAL": 7,
            "QUINCENAL": 15,
            "MENSUAL": 30
        }

        fecha_inicio = date.today()

        fecha_fin = fecha_inicio + timedelta(
            days=dias[tipo]
        )

        if presupuesto_actual.empty:

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
                "✅ Presupuesto creado"
            )

        else:

            ejecutar_query(
                """
                UPDATE gastos.presupuestos
                SET
                    tipo_periodo = :tipo_periodo,
                    monto = :monto,
                    fecha_inicio = :fecha_inicio,
                    fecha_fin = :fecha_fin
                WHERE id = :id
                """,
                {
                    "id":
                        int(
                            presupuesto_actual.iloc[0]["id"]
                        ),
                    "tipo_periodo":
                        tipo,
                    "monto":
                        monto,
                    "fecha_inicio":
                        fecha_inicio,
                    "fecha_fin":
                        fecha_fin
                }
            )

            st.success(
                "✅ Presupuesto actualizado"
            )

        st.rerun()

    historial = obtener_dataframe(
        """
        SELECT
            id,
            tipo_periodo,
            monto,
            fecha_inicio,
            fecha_fin,
            fecha_creacion
        FROM gastos.presupuestos
        WHERE usuario_id = :uid
        ORDER BY id DESC
        LIMIT 10
        """,
        {"uid": uid}
    )

    st.markdown("### Historial")

    st.dataframe(
        historial,
        use_container_width=True
    )