CREATE SCHEMA IF NOT EXISTS gastos;

CREATE TABLE IF NOT EXISTS gastos.usuarios (
 id SERIAL PRIMARY KEY,
 nombre VARCHAR(100),
 email VARCHAR(200) UNIQUE,
 password_hash TEXT,
 fecha_alta TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gastos.presupuestos (
 id SERIAL PRIMARY KEY,
 usuario_id INTEGER,
 tipo_periodo VARCHAR(20),
 monto NUMERIC(12,2),
 fecha_inicio DATE,
 fecha_fin DATE,
 activo BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS gastos.movimientos (
 id SERIAL PRIMARY KEY,
 usuario_id INTEGER REFERENCES gastos.usuarios(id),
 fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 tipo VARCHAR(20),
 concepto VARCHAR(255),
 categoria VARCHAR(100),
 monto NUMERIC(12,2),
 origen_ingreso VARCHAR(100),
 texto_original TEXT
);

CREATE TABLE IF NOT EXISTS gastos.recordatorios (
 id SERIAL PRIMARY KEY,
 usuario_id INTEGER REFERENCES gastos.usuarios(id),
 descripcion VARCHAR(255),
 monto NUMERIC(12,2),
 fecha_vencimiento DATE,
 dias_anticipacion INTEGER DEFAULT 3,
 frecuencia VARCHAR(20) DEFAULT 'UNICO',
 pagado BOOLEAN DEFAULT FALSE,
 fecha_ultimo_pago DATE,
 fecha_proxima_alerta DATE,
 fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gastos.diccionario_usuario (
 id SERIAL PRIMARY KEY,
 usuario_id INTEGER REFERENCES gastos.usuarios(id),
 frase VARCHAR(255),
 accion VARCHAR(50),
 categoria VARCHAR(100),
 fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Columnas agregadas después de la v1 del schema.
-- Con IF NOT EXISTS son seguras de correr sobre una base ya existente.
ALTER TABLE gastos.presupuestos ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE gastos.movimientos ADD COLUMN IF NOT EXISTS origen_ingreso VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_movimientos_usuario ON gastos.movimientos(usuario_id);
CREATE INDEX IF NOT EXISTS idx_recordatorios_usuario ON gastos.recordatorios(usuario_id);
CREATE INDEX IF NOT EXISTS idx_presupuestos_usuario ON gastos.presupuestos(usuario_id);

-- =====================================================
-- FASE 3: CUENTAS COMPARTIDAS + SUSCRIPCIONES (SaaS)
-- =====================================================
--
-- Modelo: los datos financieros ya no pertenecen a un usuario
-- individual, sino a una "cuenta" (tenant). Un usuario pertenece a
-- UNA cuenta a la vez. Una cuenta INDIVIDUAL tiene 1 miembro; una
-- cuenta FAMILIAR puede tener varios, todos viendo los mismos
-- movimientos/presupuesto/recordatorios.
--
-- IMPORTANTE: después de correr este script en una base que ya
-- tiene datos, corre sql/migrar_cuentas.py una sola vez para crear
-- una cuenta individual por cada usuario existente y "rellenar"
-- cuenta_id en sus filas — si no, esos usuarios quedarán sin cuenta
-- y la app no podrá mostrarles nada.

CREATE TABLE IF NOT EXISTS gastos.cuentas (
 id SERIAL PRIMARY KEY
);

ALTER TABLE gastos.cuentas ADD COLUMN IF NOT EXISTS nombre VARCHAR(150);
ALTER TABLE gastos.cuentas ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) NOT NULL DEFAULT 'INDIVIDUAL'; -- INDIVIDUAL | FAMILIAR
ALTER TABLE gastos.cuentas ADD COLUMN IF NOT EXISTS codigo_invitacion VARCHAR(10);
ALTER TABLE gastos.cuentas ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

CREATE UNIQUE INDEX IF NOT EXISTS uq_cuentas_codigo_invitacion ON gastos.cuentas(codigo_invitacion);

ALTER TABLE gastos.usuarios ADD COLUMN IF NOT EXISTS cuenta_id INTEGER REFERENCES gastos.cuentas(id);
ALTER TABLE gastos.usuarios ADD COLUMN IF NOT EXISTS rol_cuenta VARCHAR(20) DEFAULT 'ADMIN'; -- ADMIN | MIEMBRO
ALTER TABLE gastos.usuarios ADD COLUMN IF NOT EXISTS nombre_agente VARCHAR(50) DEFAULT 'Queda'; -- palabra de activación por voz, elegida por el usuario
ALTER TABLE gastos.usuarios ADD COLUMN IF NOT EXISTS token_sesion_hash VARCHAR(128); -- "recuérdame" — nunca se guarda el token en claro, solo su hash
ALTER TABLE gastos.usuarios ADD COLUMN IF NOT EXISTS token_sesion_expira TIMESTAMP;

ALTER TABLE gastos.movimientos ADD COLUMN IF NOT EXISTS cuenta_id INTEGER REFERENCES gastos.cuentas(id);
ALTER TABLE gastos.presupuestos ADD COLUMN IF NOT EXISTS cuenta_id INTEGER REFERENCES gastos.cuentas(id);
ALTER TABLE gastos.recordatorios ADD COLUMN IF NOT EXISTS cuenta_id INTEGER REFERENCES gastos.cuentas(id);
ALTER TABLE gastos.diccionario_usuario ADD COLUMN IF NOT EXISTS cuenta_id INTEGER REFERENCES gastos.cuentas(id);

CREATE INDEX IF NOT EXISTS idx_usuarios_cuenta ON gastos.usuarios(cuenta_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_cuenta ON gastos.movimientos(cuenta_id);
CREATE INDEX IF NOT EXISTS idx_presupuestos_cuenta ON gastos.presupuestos(cuenta_id);
CREATE INDEX IF NOT EXISTS idx_recordatorios_cuenta ON gastos.recordatorios(cuenta_id);

-- Catálogo de planes. precio_centavos está en centavos de MXN
-- (1000 = $10.00) para evitar errores de redondeo con floats.
-- stripe_price_id lo llenas tú desde el Dashboard de Stripe
-- (Producto → Precio) — cambiar el precio ahí NO requiere tocar
-- código, solo actualizar esta fila.
--
-- CREATE TABLE + ALTER ... ADD COLUMN IF NOT EXISTS para cada
-- columna (en vez de meter todo en el CREATE TABLE): así, si la
-- tabla YA existía con otra estructura (como te pasó con
-- suscripciones, que ya la tenías creada de antes con otras
-- columnas), el script igual la deja con la estructura que Queda
-- necesita, en vez de quedarse callado porque "la tabla ya existe".

CREATE TABLE IF NOT EXISTS gastos.planes (
 id SERIAL PRIMARY KEY
);

ALTER TABLE gastos.planes ADD COLUMN IF NOT EXISTS slug VARCHAR(30);
ALTER TABLE gastos.planes ADD COLUMN IF NOT EXISTS nombre VARCHAR(100);
ALTER TABLE gastos.planes ADD COLUMN IF NOT EXISTS tipo_cuenta VARCHAR(20); -- INDIVIDUAL | FAMILIAR
ALTER TABLE gastos.planes ADD COLUMN IF NOT EXISTS precio_centavos INTEGER;
ALTER TABLE gastos.planes ADD COLUMN IF NOT EXISTS limite_miembros INTEGER NOT NULL DEFAULT 1;
ALTER TABLE gastos.planes ADD COLUMN IF NOT EXISTS stripe_price_id VARCHAR(100);
ALTER TABLE gastos.planes ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT TRUE;
ALTER TABLE gastos.planes ADD COLUMN IF NOT EXISTS limite_recordatorios INTEGER; -- NULL = sin límite
ALTER TABLE gastos.planes ADD COLUMN IF NOT EXISTS incluye_ia BOOLEAN DEFAULT TRUE; -- Asistente IA (texto/voz) + narrativa con IA en Inicio

CREATE UNIQUE INDEX IF NOT EXISTS uq_planes_slug ON gastos.planes(slug);

INSERT INTO gastos.planes (slug, nombre, tipo_cuenta, precio_centavos, limite_miembros, stripe_price_id)
VALUES
 ('basico', 'Básico', 'INDIVIDUAL', 1000, 1, 'price_PENDIENTE_BASICO'),
 ('individual', 'Individual', 'INDIVIDUAL', 4900, 1, 'price_PENDIENTE_INDIVIDUAL'),
 ('familiar', 'Familiar', 'FAMILIAR', 9900, 5, 'price_PENDIENTE_FAMILIAR')
ON CONFLICT (slug) DO NOTHING;

-- Diferencias reales entre planes (con UPDATE, no solo en el INSERT
-- de arriba, para que también apliquen si esas filas ya existían
-- de una corrida anterior del script):
-- - Básico: registro manual completo (movimientos, presupuesto,
--   historial, dashboard, recordatorios) pero SIN Asistente IA
--   (ni texto ni voz) y con tope de 5 recordatorios activos.
-- - Individual: todo lo anterior + Asistente IA + narrativa
--   generada con IA en Inicio, sin tope de recordatorios.
-- - Familiar: todo lo de Individual + hasta 5 miembros compartiendo
--   la misma cuenta.
UPDATE gastos.planes SET limite_recordatorios = 5, incluye_ia = FALSE WHERE slug = 'basico';
UPDATE gastos.planes SET limite_recordatorios = NULL, incluye_ia = TRUE WHERE slug = 'individual';
UPDATE gastos.planes SET limite_recordatorios = NULL, incluye_ia = TRUE WHERE slug = 'familiar';

-- Una fila por cuenta con su estado de pago. status sigue el
-- vocabulario de Stripe: incomplete | trialing | active | past_due
-- | canceled. plan_id y los campos stripe_* se llenan cuando el
-- webhook confirma el pago (ver webhook_service/).

CREATE TABLE IF NOT EXISTS gastos.suscripciones (
 id SERIAL PRIMARY KEY
);

ALTER TABLE gastos.suscripciones ADD COLUMN IF NOT EXISTS cuenta_id INTEGER REFERENCES gastos.cuentas(id);
ALTER TABLE gastos.suscripciones ADD COLUMN IF NOT EXISTS plan_id INTEGER REFERENCES gastos.planes(id);
ALTER TABLE gastos.suscripciones ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(100);
ALTER TABLE gastos.suscripciones ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(100);
ALTER TABLE gastos.suscripciones ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'incomplete';
ALTER TABLE gastos.suscripciones ADD COLUMN IF NOT EXISTS fecha_inicio TIMESTAMP;
ALTER TABLE gastos.suscripciones ADD COLUMN IF NOT EXISTS fin_periodo_actual TIMESTAMP;
ALTER TABLE gastos.suscripciones ADD COLUMN IF NOT EXISTS cancelar_al_final_periodo BOOLEAN DEFAULT FALSE;
ALTER TABLE gastos.suscripciones ADD COLUMN IF NOT EXISTS fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Si tu tabla vieja tenía "usuario_id" y/o "plan"/"activa" (texto
-- libre) de una versión anterior, se quedan ahí sin usarse — no
-- estorban, pero si quieres limpiarlos después de confirmar que
-- todo funciona: ALTER TABLE gastos.suscripciones DROP COLUMN IF EXISTS usuario_id;
-- (y lo mismo para "plan"/"activa" si existían con esos nombres).

CREATE INDEX IF NOT EXISTS idx_suscripciones_cuenta ON gastos.suscripciones(cuenta_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_suscripciones_stripe_sub
 ON gastos.suscripciones(stripe_subscription_id)
 WHERE stripe_subscription_id IS NOT NULL;
