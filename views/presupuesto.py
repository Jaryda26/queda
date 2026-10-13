import streamlit as st

from services.presupuesto_service import (
    NOMBRES_DIA,
    guardar_presupuesto,
    obtener_estado_presupuesto,
)
from db import obtener_dataframe


def pantalla_presupuesto():

    uid = st.session_state["user_id"]
    cuenta_id = st.session_state["cuenta_id"]

    st.title("🎯 Presupuesto")

    st.caption(
        "El presupuesto es un TOPE DE GASTO por periodo. Semanal: 7 días "
        "desde el día que elijas (por ejemplo viernes a jueves si te "
        "pagan los viernes). Quincenal: del 1 al 15 y del 16 al fin de "
        "mes. Mensual: el mes natural."
    )

    actual = obtener_estado_presupuesto(cuenta_id)

    monto_default = 0.0
    tipo_default = "MENSUAL"
    dia_default = 0

    if actual:

        monto_default = float(actual["monto"])
        tipo_default = actual["tipo_periodo"]
        dia_default = int(actual["dia_inicio"])

        st.info(
            f"✅ Presupuesto {tipo_default.lower()}: "
            f"${monto_default:,.2f}\n\n"
            f"Periodo actual: {actual['fecha_inicio']} al "
            f"{actual['fecha_fin']} — llevas "
            f"${actual['gastado']:,.2f} ({actual['porcentaje']:.0f}%), "
            f"te quedan ${actual['restante']:,.2f} y "
            f"{actual['dias_restantes']} día(s)."
        )

    opciones = ["SEMANAL", "QUINCENAL", "MENSUAL"]

    tipo = st.selectbox(
        "Periodo",
        opciones,
        index=opciones.index(tipo_default)
    )

    dia = dia_default

    if tipo == "SEMANAL":

        dia = st.selectbox(
            "La semana inicia el",
            list(range(7)),
            index=dia_default,
            format_func=lambda i: NOMBRES_DIA[i].capitalize()
        )

        st.caption(
            f"Tu semana irá de {NOMBRES_DIA[dia]} a "
            f"{NOMBRES_DIA[(dia + 6) % 7]}."
        )

    monto = st.number_input(
        "Monto",
        min_value=0.0,
        value=monto_default
    )

    texto_boton = (
        "Actualizar Presupuesto" if actual else "Crear Presupuesto"
    )

    if st.button(texto_boton):

        try:

            guardar_presupuesto(uid, cuenta_id, tipo, monto, dia)

            st.success("✅ Presupuesto guardado")

            st.rerun()

        except ValueError as e:

            st.warning(str(e))

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
        WHERE cuenta_id = :cuenta_id
        ORDER BY id DESC
        LIMIT 10
        """,
        {"cuenta_id": cuenta_id}
    )

    st.markdown("### Historial")

    st.dataframe(
        historial,
        use_container_width=True
    )
