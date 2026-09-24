import streamlit as st
from services.usuario_service import registrar_usuario


def pantalla_registro():

    st.title("📝 Crear cuenta")

    with st.form("form_registro"):

        nombre = st.text_input("Nombre")
        email = st.text_input("Correo")
        password = st.text_input(
            "Contraseña",
            type="password",
            help="Mínimo 8 caracteres."
        )

        codigo_invitacion = st.text_input(
            "Código de invitación (opcional)",
            help=(
                "¿Alguien de tu familia ya tiene Queda y te "
                "invitó? Pon aquí su código para unirte "
                "directo a su cuenta en vez de crear la tuya."
            )
        )

        crear = st.form_submit_button("Crear cuenta")

    if crear:

        ok, mensaje = registrar_usuario(
            nombre,
            email,
            password,
            codigo_invitacion
        )

        if ok:
            st.success(f"✅ {mensaje}")
        else:
            st.error(f"⚠️ {mensaje}")
