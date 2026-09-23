# Fase 3 — Cuentas compartidas + Suscripciones (Stripe)

## El cambio de fondo

Antes, todo (movimientos, presupuesto, recordatorios) pertenecía
directamente a un `usuario_id`. Ahora pertenece a una **cuenta**
(`gastos.cuentas`), y un usuario pertenece a UNA cuenta a la vez:

- Cuenta **INDIVIDUAL**: 1 miembro (tú).
- Cuenta **FAMILIAR**: varios miembros viendo los mismos
  movimientos/presupuesto/recordatorios, cada uno con su rol
  (`ADMIN` o `MIEMBRO`).

Cada `INSERT` sigue guardando `usuario_id` (quién de la familia lo
hizo) **y** `cuenta_id` (de quién son los datos) — así que a futuro
se puede mostrar "quién gastó qué" dentro de una cuenta familiar.

## Planes y precios (los que armé — cámbialos cuando quieras)

| Plan       | Precio MXN/mes | Tipo       | Miembros |
|------------|-----------------|------------|----------|
| Básico     | $10.00          | Individual | 1        |
| Individual | $49.00          | Individual | 1        |
| Familiar   | $99.00          | Familiar   | 5        |

Viven en `gastos.planes` — cambiar el precio ahí (y en Stripe) no
requiere tocar código.

## Archivos nuevos

- **`sql/schema.sql`** (sección "FASE 3"): tablas `cuentas`,
  `planes`, `suscripciones`; columnas `cuenta_id`/`rol_cuenta` en
  `usuarios`; columna `cuenta_id` en movimientos/presupuestos/
  recordatorios/diccionario_usuario.
- **`sql/migrar_cuentas.py`**: corre UNA VEZ después del schema, en
  una base con datos existentes. Le crea una cuenta individual a
  cada usuario ya existente, rellena `cuenta_id` en todo su
  historial, y le da una suscripción `active` con el plan
  Individual (sin datos de Stripe) para que tu propio uso actual no
  quede bloqueado por el paywall.
- **`services/cuenta_service.py`**: miembros de la cuenta, generar
  código de invitación, unirse a una cuenta con un código.
- **`services/billing_service.py`**: catálogo de planes, crear
  sesión de Stripe Checkout, link al Portal de Cliente (para que el
  usuario cambie tarjeta/cancele sin que construyamos nada de eso),
  y sincronización manual (polling) del estado real desde Stripe.
- **`views/suscripcion.py`**: pantalla donde el usuario ve su plan
  actual y elige uno nuevo.
- **`views/cuenta.py`**: miembros, generar/mostrar código de
  invitación (si eres admin de una cuenta Familiar), unirse a otra
  cuenta con un código.
- **`webhook_service/`**: servicio FastAPI **aparte** (no es
  Streamlit) que recibe los eventos de Stripe en tiempo real y
  mantiene `gastos.suscripciones` al día. Trae su propio
  `requirements.txt`, `.env.example` y un `README.md` con los pasos
  para desplegarlo y registrar el endpoint en Stripe.

## Bug real que encontré y corregí en `db.py`

Necesitaba una forma de hacer `INSERT ... RETURNING id` para crear
una cuenta y usar su id al toque. Antes de escribir la función lo
probé con sqlite: `ejecutar_query()` cierra la conexión al salir del
`with`, así que un `fetchone()` sobre lo que regresa **truena**
(`cannot commit transaction — SQL statements in progress` en
sqlite; en Postgres el síntoma es distinto pero el problema de fondo
es el mismo: la conexión ya se cerró). Agregué
`ejecutar_query_retornando()`, que hace el `fetchone()` DENTRO de la
transacción — quedó probado con un caso mínimo antes de usarlo en
`registrar_usuario()`.

## `registrar_usuario()` ahora es atómico

Crear la cuenta + el usuario + su suscripción inicial va en una
sola transacción (`with engine.begin() as conn:` directo en
`usuario_service.py`) — si algo falla a la mitad, no queda una
cuenta huérfana sin usuario.

## El paywall

En `app.py`: si la cuenta no tiene una suscripción con status
`active` o `trialing`, el usuario solo puede ver 💳 Suscripción o
cerrar sesión — nada más carga (ni el menú, ni el micrófono). No
hay plan gratis de verdad: el más barato cuesta $10.

## Unirse a una cuenta familiar — limitación conocida

Cuando alguien usa un código de invitación para unirse a una cuenta
Familiar, su `cuenta_id` cambia pero **su historial financiero
anterior se queda en su cuenta vieja** — deja de ser visible, no se
borra ni se mezcla automáticamente. Migrar/fusionar ese historial a
la cuenta nueva es una decisión de producto (¿debería mezclarse
siempre? ¿preguntar primero?) que dejé fuera de esta fase a
propósito — dímelo cuando lo pensemos y lo construyo.

## Lo que TÚ tienes que hacer (fuera de código)

1. Correr el `sql/schema.sql` actualizado contra tu base.
2. Correr `python sql/migrar_cuentas.py` una vez (para no quedar
   bloqueado por el paywall con tu usuario actual).
3. En el Dashboard de Stripe: crear 3 Productos/Precios (o los que
   definas) y pegar sus `price_id` reales en `gastos.planes`
   (reemplazando los `price_PENDIENTE_*`).
4. Agregar a `.streamlit/secrets.toml`:
   ```toml
   STRIPE_SECRET_KEY = "sk_live_..."
   APP_URL = "https://tu-app.streamlit.app"
   ```
5. Desplegar `webhook_service/` (instrucciones en su propio
   README.md) y registrar su URL + eventos en Stripe.

## Validado

`py_compile` + `pyflakes` sobre TODO el árbol (incluyendo
`webhook_service/`, que es un paquete Python independiente) — 0
errores.
