import streamlit as st

from db import ejecutar_query
from db import obtener_dataframe


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

✅ Ya quedó Sears → Pago recordatorio
"""
    )

    frase = st.text_input(
        "Frase"
    )

    accion = st.selectbox(
        "Acción",
        [
            "REGISTRAR_GASTO",
            "REGISTRAR_INGRESO",
            "PAGAR_RECORDATORIO",
            "POSPONER_RECORDATORIO"
        ]
    )

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
**Acción:** {row['accion']}

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