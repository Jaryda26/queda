import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from services.usuario_service import validar_usuario, crear_token_sesion
from auth.session import login_user


def pantalla_login(cookie_manager):

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
                    usuario.get("rol_cuenta", "ADMIN"),
                    usuario.get("nombre_agente", "Queda")
                )

                # Sesión persistente: guarda un token en una
                # cookie de 30 días para no pedir login otra vez
                # cada que se cierra/reabre la pestaña. Nunca debe
                # bloquear el login en sí — si la base todavía no
                # tiene las columnas de esta función (falta correr
                # sql/schema.sql), simplemente no queda "recordado"
                # esta vez, pero el login sigue funcionando.

                try:

                    token = crear_token_sesion(
                        int(usuario["id"])
                    )

                    cookie_manager.set(
                        "queda_token",
                        token,
                        expires_at=(
                            datetime.now() + timedelta(days=30)
                        ),
                        key="guardar_queda_token"
                    )

                except Exception:
                    pass

                st.rerun()

        else:

            st.error(
                "Credenciales inválidas"
            )