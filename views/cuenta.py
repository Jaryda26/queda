import streamlit as st

from services.cuenta_service import (
    obtener_miembros,
    obtener_o_crear_codigo,
    unirse_a_cuenta
)
from services.billing_service import obtener_suscripcion
from services.usuario_service import actualizar_nombre_agente


def pantalla_cuenta():

    st.title("👨‍👩‍👧 Mi cuenta")

    cuenta_id = st.session_state["cuenta_id"]
    rol = st.session_state.get("rol_cuenta")

    miembros_df = obtener_miembros(cuenta_id)
    sub_df = obtener_suscripcion(cuenta_id)

    tipo_cuenta = (
        sub_df.iloc[0]["tipo_cuenta"]
        if not sub_df.empty and sub_df.iloc[0]["tipo_cuenta"]
        else "INDIVIDUAL"
    )

    st.markdown("### Nombre de tu asistente")

    st.caption(
        "Así vas a activar la escucha por voz diciendo su nombre "
        "— cámbialo por el que quieras (ej. \"Jarvis\", \"Ana\")."
    )

    col_nombre, col_boton = st.columns([3, 1])

    with col_nombre:

        nuevo_nombre = st.text_input(
            "Nombre",
            value=st.session_state.get("nombre_agente", "Queda"),
            label_visibility="collapsed"
        )

    with col_boton:

        if st.button("Guardar", use_container_width=True):

            ok, mensaje = actualizar_nombre_agente(
                st.session_state["user_id"],
                nuevo_nombre
            )

            if ok:

                st.session_state["nombre_agente"] = (
                    nuevo_nombre.strip()
                )

                st.success(mensaje)
                st.rerun()

            else:

                st.error(mensaje)

    st.markdown("---")
    st.markdown("### Miembros")

    for _, m in miembros_df.iterrows():

        etiqueta = (
            "👑 Admin" if m["rol_cuenta"] == "ADMIN" else "Miembro"
        )

        st.markdown(f"- **{m['nombre']}** — {etiqueta}")

    st.markdown("---")

    if tipo_cuenta == "FAMILIAR" and rol == "ADMIN":

        st.markdown("### Invitar a alguien")

        codigo = obtener_o_crear_codigo(cuenta_id)

        st.code(codigo)

        st.caption(
            "Comparte este código con quien quieras que se una "
            "a tu cuenta familiar. Ellos deben crear su propia "
            "cuenta en Queda primero (o ya tener una) y luego "
            "usar el código abajo."
        )

    elif tipo_cuenta != "FAMILIAR":

        st.info(
            "Tu plan actual es individual. Cambia al plan "
            "Familiar en 💳 Suscripción para invitar a alguien."
        )

    st.markdown("---")
    st.markdown("### Unirme a otra cuenta")

    st.caption(
        "Si alguien te compartió un código de invitación, tu "
        "historial actual dejará de verse (se queda guardado en "
        "tu cuenta anterior) y vas a ver los datos de la cuenta "
        "a la que te unas."
    )

    codigo_input = st.text_input("Código de invitación")

    if st.button("Unirme"):

        if not codigo_input.strip():

            st.warning("Escribe un código.")

        else:

            ok, mensaje = unirse_a_cuenta(
                st.session_state["user_id"],
                codigo_input
            )

            if ok:

                st.success(
                    f"{mensaje} Cierra sesión y vuelve a entrar "
                    f"para ver los datos de tu nueva cuenta."
                )

            else:

                st.error(mensaje)
