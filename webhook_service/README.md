# Queda — Webhook Service

Servicio aparte (FastAPI) que recibe los eventos de Stripe en tiempo
real y mantiene `gastos.suscripciones` sincronizada. No es parte de
la app de Streamlit — Streamlit no puede exponer un endpoint propio,
por eso esto vive y se despliega solo.

## 1. Correrlo local (para probar)

```bash
cd webhook_service
pip install -r requirements.txt
cp .env.example .env   # rellena DATABASE_URL, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
uvicorn main:app --reload --port 8000
```

Para probar webhooks en local sin desplegar nada, usa la CLI de
Stripe:

```bash
stripe listen --forward-to localhost:8000/stripe-webhook
```

Ese comando te da un `whsec_...` de prueba — úsalo como
`STRIPE_WEBHOOK_SECRET` mientras pruebas local.

## 2. Desplegarlo (elige uno)

Cualquier plataforma que corra un contenedor Python sirve. Ejemplos:

**Render** (más simple):
1. New → Web Service → conecta este repo (o solo la carpeta
   `webhook_service/` como repo aparte).
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Agrega las 3 variables de entorno en Settings → Environment.

**Railway / Fly.io**: mismo patrón — variables de entorno +
`uvicorn main:app --host 0.0.0.0 --port $PORT`.

Al terminar, vas a tener una URL pública tipo
`https://queda-webhooks.onrender.com`.

## 3. Registrar el endpoint en Stripe

1. Dashboard de Stripe → Developers → Webhooks → Add endpoint.
2. Endpoint URL: `https://TU-URL/stripe-webhook`
3. Eventos a escuchar:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
4. Stripe te da un **Signing secret** (`whsec_...`) — ese es tu
   `STRIPE_WEBHOOK_SECRET` de producción. Actualízalo en las
   variables de entorno de donde lo desplegaste.

## 4. Antes de todo esto, en el Dashboard de Stripe

Necesitas crear 3 Productos con sus Precios (uno por plan:
Básico $10, Individual $49, Familiar $99 MXN/mes — o los precios
que definas) y copiar cada `price_id` a la tabla `gastos.planes`
de tu base (columna `stripe_price_id`), reemplazando los
`price_PENDIENTE_*` que dejé como placeholder en `sql/schema.sql`.

```sql
UPDATE gastos.planes SET stripe_price_id = 'price_XXXX' WHERE slug = 'basico';
UPDATE gastos.planes SET stripe_price_id = 'price_YYYY' WHERE slug = 'individual';
UPDATE gastos.planes SET stripe_price_id = 'price_ZZZZ' WHERE slug = 'familiar';
```

También agrega a `.streamlit/secrets.toml` de la app de Streamlit
(no de este servicio):

```toml
STRIPE_SECRET_KEY = "sk_live_..."
APP_URL = "https://tu-app.streamlit.app"
```
