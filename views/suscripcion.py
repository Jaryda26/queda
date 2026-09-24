import streamlit as st
import pandas as pd

from services.billing_service import (
    obtener_planes,
    obtener_suscripcion,
    crear_checkout_session,
    crear_portal_facturacion,
    sincronizar_suscripcion
)


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

                if plan["incluye_ia"]:
                    st.markdown("✅ Asistente IA (texto y voz)")
                else:
                    st.markdown("🔒 Sin Asistente IA")

                if pd.isna(plan["limite_recordatorios"]):
                    st.markdown("🔔 Recordatorios ilimitados")
                else:
                    st.markdown(
                        f"🔔 Hasta "
                        f"{int(plan['limite_recordatorios'])} "
                        f"recordatorios activos"
                    )

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
