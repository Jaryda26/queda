"""
Servicio aparte (NO es parte de la app de Streamlit) que recibe los
eventos de Stripe en tiempo real y actualiza gastos.suscripciones.

Por qué existe como servicio aparte: Streamlit no puede exponer una
URL propia tipo /stripe-webhook, así que esto se despliega como su
propio servicio (Render, Railway, Fly.io, un VPS, lo que uses) con
su propia URL pública, apuntando a LA MISMA base de datos Postgres
que usa Queda.

Ejecutar localmente:
    uvicorn main:app --reload --port 8000

Variables de entorno requeridas (ver .env.example):
    DATABASE_URL          — misma base que usa la app de Streamlit
    STRIPE_SECRET_KEY      — sk_live_... o sk_test_...
    STRIPE_WEBHOOK_SECRET  — whsec_... (te lo da Stripe al registrar
                              el endpoint, ver README.md)
"""

import os
from datetime import datetime, timezone

import stripe
from fastapi import FastAPI, Request, HTTPException

from db import ejecutar_query, obtener_dataframe

app = FastAPI(title="Queda — Webhooks de Stripe")

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
STRIPE_WEBHOOK_SECRET = os.environ["STRIPE_WEBHOOK_SECRET"]


@app.get("/")
def salud():
    return {"status": "ok"}


@app.post("/stripe-webhook")
async def stripe_webhook(request: Request):

    payload = await request.body()
    firma = request.headers.get("stripe-signature")

    try:

        evento = stripe.Webhook.construct_event(
            payload,
            firma,
            STRIPE_WEBHOOK_SECRET
        )

    except (ValueError, stripe.error.SignatureVerificationError):

        raise HTTPException(
            status_code=400,
            detail="Firma inválida — ¿STRIPE_WEBHOOK_SECRET correcto?"
        )

    tipo = evento["type"]
    data = evento["data"]["object"]

    if tipo == "checkout.session.completed":
        _manejar_checkout_completado(data)

    elif tipo in (
        "customer.subscription.created",
        "customer.subscription.updated"
    ):
        _manejar_suscripcion_actualizada(data)

    elif tipo == "customer.subscription.deleted":
        _manejar_suscripcion_cancelada(data)

    elif tipo == "invoice.payment_failed":
        _manejar_pago_fallido(data)

    return {"received": True}


def _manejar_checkout_completado(session):
    """
    Primer link entre nuestra cuenta y la suscripción real de
    Stripe: usamos client_reference_id/metadata (que mandamos al
    crear el Checkout Session) para saber a qué cuenta pertenece.
    """

    cuenta_id = (
        session.get("client_reference_id")
        or session.get("metadata", {}).get("cuenta_id")
    )

    plan_slug = session.get("metadata", {}).get("plan_slug")
    stripe_subscription_id = session.get("subscription")
    stripe_customer_id = session.get("customer")

    if not cuenta_id or not stripe_subscription_id:
        return

    plan_id = None

    if plan_slug:

        plan_df = obtener_dataframe(
            "SELECT id FROM gastos.planes WHERE slug = :slug",
            {"slug": plan_slug}
        )

        if not plan_df.empty:
            plan_id = int(plan_df.iloc[0]["id"])

    sub_stripe = stripe.Subscription.retrieve(
        stripe_subscription_id
    )

    fin_periodo = datetime.fromtimestamp(
        sub_stripe["current_period_end"],
        tz=timezone.utc
    )

    ejecutar_query(
        """
        UPDATE gastos.suscripciones
        SET
            plan_id = COALESCE(:plan_id, plan_id),
            stripe_customer_id = :customer_id,
            stripe_subscription_id = :sub_id,
            status = :status,
            fin_periodo_actual = :fin_periodo,
            fecha_inicio = COALESCE(fecha_inicio, CURRENT_TIMESTAMP),
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE cuenta_id = :cuenta_id
        """,
        {
            "plan_id": plan_id,
            "customer_id": stripe_customer_id,
            "sub_id": stripe_subscription_id,
            "status": sub_stripe["status"],
            "fin_periodo": fin_periodo,
            "cuenta_id": int(cuenta_id)
        }
    )


def _manejar_suscripcion_actualizada(sub_stripe):

    fin_periodo = datetime.fromtimestamp(
        sub_stripe["current_period_end"],
        tz=timezone.utc
    )

    ejecutar_query(
        """
        UPDATE gastos.suscripciones
        SET
            status = :status,
            fin_periodo_actual = :fin_periodo,
            cancelar_al_final_periodo = :cancelar,
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE stripe_subscription_id = :sub_id
        """,
        {
            "status": sub_stripe["status"],
            "fin_periodo": fin_periodo,
            "cancelar": sub_stripe.get(
                "cancel_at_period_end", False
            ),
            "sub_id": sub_stripe["id"]
        }
    )


def _manejar_suscripcion_cancelada(sub_stripe):

    ejecutar_query(
        """
        UPDATE gastos.suscripciones
        SET status = 'canceled', fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE stripe_subscription_id = :sub_id
        """,
        {"sub_id": sub_stripe["id"]}
    )


def _manejar_pago_fallido(invoice):

    stripe_subscription_id = invoice.get("subscription")

    if not stripe_subscription_id:
        return

    ejecutar_query(
        """
        UPDATE gastos.suscripciones
        SET status = 'past_due', fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE stripe_subscription_id = :sub_id
        """,
        {"sub_id": stripe_subscription_id}
    )
