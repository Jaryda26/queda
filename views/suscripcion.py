import streamlit as st
import pandas as pd

from services.billing_service import (
    obtener_planes,
    obtener_suscripcion,
    crear_checkout_session,
    crear_portal_facturacion,
    sincronizar_suscripcion
)
from services.plan_ia_service import estado_ia, limite_ia_diario


def _url_base():

    return st.secrets.get(
        "APP_URL",
        "http://localhost:8501"
    )


def pantalla_suscripcion():

    st.title("💳 Tu plan")

    cuenta_id = st.session_state["cuenta_id"]

    sub_df = obtener_suscripcion(cuenta_id)

    tiene_activa = (
        not sub_df.empty
        and sub_df.iloc[0]["status"] in ("active", "trialing")
    )

    if tiene_activa:

        sub = sub_df.iloc[0]

        st.success(
            f"Plan activo: **{sub['plan_nombre']}** — "
            f"${sub['precio_centavos'] / 100:,.2f} MXN/mes"
        )

        if sub["fin_periodo_actual"] is not None:

            st.caption(
                f"Se renueva el "
                f"{sub['fin_periodo_actual']:%d/%m/%Y}"
            )

        cupo = estado_ia(
            cuenta_id,
            {
                "incluye_ia": bool(sub["incluye_ia"]),
                "plan_slug": sub["plan_slug"]
            }
        )

        if cupo["incluye_ia"]:

            st.info(
                f"🤖 Consultas con IA hoy: {cupo['ia_usadas_hoy']} de "
                f"{cupo['ia_limite_diario']} "
                f"(te quedan {cupo['ia_restantes']}). Se reinicia a "
                "medianoche. Comandos, consultas calculadas, metas y "
                "registro simple no gastan cupo."
            )

        else:

            st.info(
                "Tu plan funciona sin IA: comandos de voz, registro "
                "simple, consultas calculadas y metas de ahorro. "
                "Sube a Individual o Familiar para frases libres y "
                "consejos personalizados con IA."
            )

        if sub["cancelar_al_final_periodo"]:

            st.warning(
                "Se cancelará al final del periodo actual."
            )

        col1, col2 = st.columns(2)

        with col1:

            if st.button("🔄 Actualizar estado desde Stripe"):

                try:

                    estado = sincronizar_suscripcion(cuenta_id)

                    st.info(f"Estado actualizado: {estado}")
                    st.rerun()

                except Exception as e:

                    st.error(
                        f"No se pudo consultar Stripe: {e}"
                    )

        with col2:

            try:

                portal_url = crear_portal_facturacion(
                    cuenta_id,
                    _url_base()
                )

                if portal_url:

                    st.link_button(
                        "🧾 Administrar pago / cancelar",
                        portal_url
                    )

            except Exception as e:

                st.caption(
                    f"Portal de facturación no disponible "
                    f"todavía: {e}"
                )

    else:

        if (
            not sub_df.empty
            and sub_df.iloc[0]["status"] == "past_due"
        ):

            st.error(
                "⚠️ Tu último pago falló. Elige un plan de nuevo "
                "o actualiza tu método de pago."
            )

        else:

            st.warning(
                "Todavía no tienes un plan activo."
            )

    st.markdown("---")
    st.markdown("### Planes disponibles")

    planes_df = obtener_planes()

    columnas = st.columns(len(planes_df))

    for col, (_, plan) in zip(columnas, planes_df.iterrows()):

        with col:

            with st.container(border=True):

                st.markdown(f"**{plan['nombre']}**")

                st.markdown(
                    f"${plan['precio_centavos'] / 100:,.2f} "
                    f"MXN/mes"
                )

                st.caption(
                    f"Hasta {plan['limite_miembros']} "
                    f"miembro(s) · {plan['tipo_cuenta'].title()}"
                )

                st.markdown("&nbsp;", unsafe_allow_html=True)

                incluye_ia = bool(plan["incluye_ia"])

                limite_ia = limite_ia_diario({
                    "incluye_ia": incluye_ia,
                    "plan_slug": plan["slug"]
                })

                caracteristicas = [
                    (True, "Movimientos, presupuesto, historial y dashboard"),
                    (
                        True,
                        "Recordatorios ilimitados"
                        if pd.isna(plan["limite_recordatorios"])
                        else (
                            f"Hasta "
                            f"{int(plan['limite_recordatorios'])} "
                            f"recordatorios activos"
                        )
                    ),
                    (True, "Comandos de voz y registro simple "
                           "(\"gasté 150 en gasolina\")"),
                    (True, "Consultas calculadas: en qué gastas más, "
                           "qué afecta tu presupuesto, cuánto llevas"),
                    (True, "Consejos según tus números y metas de ahorro"),
                    (
                        incluye_ia,
                        "Frases libres con IA (fechas, varios datos, "
                        "recordatorios hablando)"
                    ),
                    (
                        incluye_ia,
                        "Consejos personalizados con IA"
                        + (
                            f" · hasta {limite_ia} consultas de IA al día"
                            if limite_ia else ""
                        )
                    ),
                    (
                        incluye_ia,
                        "Proyección diaria redactada con IA en Inicio"
                    ),
                    (
                        plan["tipo_cuenta"] == "FAMILIAR",
                        "Cuenta compartida con familia"
                    )
                ]

                for incluido, texto in caracteristicas:

                    if incluido:
                        st.markdown(f"✅ {texto}")
                    else:
                        st.markdown(
                            f"<span style='color:#8A9B97'>"
                            f"🔒 {texto}</span>",
                            unsafe_allow_html=True
                        )

                st.markdown("&nbsp;", unsafe_allow_html=True)

                es_plan_actual = (
                    tiene_activa
                    and sub_df.iloc[0]["plan_slug"] == plan["slug"]
                )

                if es_plan_actual:

                    st.success("Tu plan actual")

                elif st.button(
                    f"Elegir {plan['nombre']}",
                    key=f"elegir_{plan['slug']}",
                    use_container_width=True
                ):

                    try:

                        url = crear_checkout_session(
                            cuenta_id,
                            st.session_state["email"],
                            plan["slug"],
                            url_exito=f"{_url_base()}/?pago=exito",
                            url_cancelado=(
                                f"{_url_base()}/?pago=cancelado"
                            )
                        )

                        st.link_button(
                            "👉 Ir a pagar con Stripe",
                            url
                        )

                    except Exception as e:

                        st.error(
                            f"No se pudo iniciar el pago: {e}"
                        )
