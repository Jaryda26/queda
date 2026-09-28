import streamlit as st

from db import ejecutar_query
from db import obtener_dataframe


ACCIONES_APRENDIZAJE = {
    "REGISTRAR_GASTO": "💸 Gasto",
    "REGISTRAR_INGRESO": "💰 Ingreso",
    "PAGAR_RECORDATORIO": "✅ Pagado (pago de un recordatorio)",
    "TERMINAR_ACTIVIDAD": "✅ Terminar actividad o cita",
    "POSPONER_RECORDATORIO": "⏰ Posponer recordatorio"
}

ACCIONES_QUE_CIERRAN_RECORDATORIO = (
    "PAGAR_RECORDATORIO",
    "TERMINAR_ACTIVIDAD",
    "POSPONER_RECORDATORIO"
)


def pantalla_aprendizaje():

    uid = st.session_state["user_id"]
    cuenta_id = st.session_state["cuenta_id"]

    st.title("🧠 Aprendizaje")

    st.markdown(
        """
### Enseña nuevas frases a Queda

Ejemplos:

✅ Ya chilló la marrana → Ingreso

✅ Ya cayó el águila → Ingreso

✅ Me eché una coca → Gasto

✅ Ya quedó Sears → Pagado (pago de un recordatorio)

✅ Listo lo del pastel → Terminar actividad o cita

✅ Mañana lo veo → Posponer recordatorio
"""
    )

    frase = st.text_input(
        "Frase"
    )

    accion = st.selectbox(
        "Acción",
        list(ACCIONES_APRENDIZAJE.keys()),
        format_func=lambda a: ACCIONES_APRENDIZAJE[a]
    )

    if accion in ACCIONES_QUE_CIERRAN_RECORDATORIO:

        categoria = st.text_input(
            "¿Qué recordatorio o actividad afecta? (opcional)",
            help=(
                "Ej. \"Comprar un pastel\". Si lo dejas vacío, "
                "toma lo que digas después de la frase: enseñando "
                "\"ya quedó\", al decir \"ya quedó Sears\" busca "
                "el recordatorio de Sears."
            )
        )

    else:

        categoria = st.text_input(
            "Categoría (opcional)"
        )

    if st.button(
        "Guardar Aprendizaje"
    ):

        if not frase.strip():

            st.warning(
                "Escribe una frase."
            )

        else:

            ejecutar_query(
                """
                INSERT INTO gastos.diccionario_usuario
                (
                    usuario_id,
                    cuenta_id,
                    frase,
                    accion,
                    categoria
                )
                VALUES
                (
                    :uid,
                    :cuenta_id,
                    :frase,
                    :accion,
                    :categoria
                )
                """,
                {
                    "uid": uid,
                    "cuenta_id": cuenta_id,
                    "frase": frase.strip(),
                    "accion": accion,
                    "categoria": categoria
                }
            )

            st.success(
                "✅ Frase aprendida correctamente"
            )

            st.rerun()

    st.markdown("---")

    st.subheader(
        "Frases aprendidas"
    )

    df = obtener_dataframe(
        """
        SELECT
            id,
            frase,
            accion,
            categoria,
            fecha_creacion
        FROM gastos.diccionario_usuario
        WHERE cuenta_id = :cuenta_id
        ORDER BY id DESC
        """,
        {"cuenta_id": cuenta_id}
    )

    if df.empty:

        st.info(
            "Aún no hay frases aprendidas."
        )

        return

    for _, row in df.iterrows():

        with st.expander(
            f"🧠 {row['frase']}"
        ):

            st.markdown(
                f"""
**Acción:** {ACCIONES_APRENDIZAJE.get(row['accion'], row['accion'])}

**Categoría:** {row['categoria']}

**Fecha:** {row['fecha_creacion']}
"""
            )

            if st.button(
                "🗑 Eliminar",
                key=f"apr_{row['id']}"
            ):

                ejecutar_query(
                    """
                    DELETE
                    FROM gastos.diccionario_usuario
                    WHERE id = :id
                    """,
                    {
                        "id": int(row["id"])
                    }
                )

                st.success(
                    "✅ Aprendizaje eliminado"
                )

                st.rerun()