from datetime import datetime, timezone

import streamlit as st
import stripe

from db import obtener_dataframe, ejecutar_query


def _configurar_stripe():

    try:

        stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]

    except Exception:

        raise RuntimeError(
            "Falta STRIPE_SECRET_KEY en st.secrets — todavía no "
            "se pueden procesar pagos."
        )

    return stripe


def obtener_planes():

    return obtener_dataframe(
        """
        SELECT *
        FROM gastos.planes
        WHERE activo = TRUE
        ORDER BY precio_centavos
        """
    )


def obtener_suscripcion(cuenta_id):

    return obtener_dataframe(
        """
        SELECT
            s.*,
            p.slug AS plan_slug,
            p.nombre AS plan_nombre,
            p.precio_centavos,
            p.tipo_cuenta,
            p.limite_miembros
        FROM gastos.suscripciones s
        LEFT JOIN gastos.planes p ON p.id = s.plan_id
        WHERE s.cuenta_id = :cuenta_id
        ORDER BY s.id DESC
        LIMIT 1
        """,
        {"cuenta_id": cuenta_id}
    )


def tiene_suscripcion_activa(cuenta_id):

    df = obtener_suscripcion(cuenta_id)

    if df.empty:
        return False

    return df.iloc[0]["status"] in ("active", "trialing")


def crear_checkout_session(
    cuenta_id,
    usuario_email,
    plan_slug,
    url_exito,
    url_cancelado
):

    client = _configurar_stripe()

    plan_df = obtener_dataframe(
        """
        SELECT *
        FROM gastos.planes
        WHERE slug = :slug AND activo = TRUE
        """,
        {"slug": plan_slug}
    )

    if plan_df.empty:

        raise ValueError(
            f"El plan '{plan_slug}' no existe o está inactivo."
        )

    plan = plan_df.iloc[0]

    sub_df = obtener_suscripcion(cuenta_id)

    stripe_customer_id = None

    if (
        not sub_df.empty
        and sub_df.iloc[0]["stripe_customer_id"]
    ):
        stripe_customer_id = sub_df.iloc[0]["stripe_customer_id"]

    parametros = {
        "mode": "subscription",
        "line_items": [
            {
                "price": plan["stripe_price_id"],
                "quantity": 1
            }
        ],
        "success_url": url_exito,
        "cancel_url": url_cancelado,
        "client_reference_id": str(cuenta_id),
        "metadata": {
            "cuenta_id": str(cuenta_id),
            "plan_slug": plan_slug
        }
    }

    if stripe_customer_id:
        parametros["customer"] = stripe_customer_id
    else:
        parametros["customer_email"] = usuario_email

    sesion = client.checkout.Session.create(**parametros)

    return sesion.url


def crear_portal_facturacion(cuenta_id, url_retorno):
    """
    Link al Portal de Cliente de Stripe, donde el usuario puede
    cambiar su tarjeta, ver facturas o cancelar — sin que
    tengamos que construir nada de eso nosotros.
    """

    client = _configurar_stripe()

    sub_df = obtener_suscripcion(cuenta_id)

    if sub_df.empty or not sub_df.iloc[0]["stripe_customer_id"]:
        return None

    sesion = client.billing_portal.Session.create(
        customer=sub_df.iloc[0]["stripe_customer_id"],
        return_url=url_retorno
    )

    return sesion.url


def sincronizar_suscripcion(cuenta_id):
    """
    Polling manual: le pregunta a Stripe el estado real de la
    suscripción de esta cuenta y actualiza la base local. Sirve
    de respaldo si el webhook tarda o no está desplegado todavía.
    """

    client = _configurar_stripe()

    sub_df = obtener_suscripcion(cuenta_id)

    if sub_df.empty or not sub_df.iloc[0]["stripe_subscription_id"]:
        return None

    stripe_subscription_id = sub_df.iloc[0]["stripe_subscription_id"]

    sub_stripe = client.Subscription.retrieve(stripe_subscription_id)

    fin_periodo_dt = datetime.fromtimestamp(
        sub_stripe["current_period_end"],
        tz=timezone.utc
    )

    ejecutar_query(
        """
        UPDATE gastos.suscripciones
        SET
            stripe_customer_id = :customer_id,
            status = :status,
            fin_periodo_actual = :fin_periodo,
            cancelar_al_final_periodo = :cancelar,
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE stripe_subscription_id = :sub_id
        """,
        {
            "customer_id": sub_stripe["customer"],
            "status": sub_stripe["status"],
            "fin_periodo": fin_periodo_dt,
            "cancelar": sub_stripe["cancel_at_period_end"],
            "sub_id": stripe_subscription_id
        }
    )

    return sub_stripe["status"]
