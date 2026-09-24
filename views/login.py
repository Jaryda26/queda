import streamlit as st
import pandas as pd

from services.usuario_service import validar_usuario
from auth.session import login_user


def pantalla_login():

    st.title("🔐 Login")

    with st.form("form_login"):

        email = st.text_input(
            "Correo"
        )

        password = st.text_input(
            "Contraseña",
            type="password"
        )

        entrar = st.form_submit_button(
            "Entrar"
        )

    if entrar:

        usuario = validar_usuario(
            email,
            password
        )

        if usuario is not None:

            cuenta_id = usuario.get("cuenta_id")

            if cuenta_id is None or pd.isna(cuenta_id):

                st.error(
                    "⚠️ Tu base de datos todavía no tiene "
                    "aplicada la migración de cuentas (Fase 3). "
                    "Corre sql/schema.sql y luego "
                    "sql/migrar_cuentas.py contra tu base de "
                    "producción — ver CHANGELOG_FASE3_COBROS.md."
                )

            else:

                login_user(
                    int(usuario["id"]),
                    usuario["nombre"],
                    usuario["email"],
                    int(cuenta_id),
                    usuario.get("rol_cuenta", "ADMIN")
                )

                st.rerun()

        else:

            st.error(
                "Credenciales inválidas"
            )