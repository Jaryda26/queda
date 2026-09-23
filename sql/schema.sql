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
 id SERIAL PRIMARY KEY,
 nombre VARCHAR(150),
 tipo VARCHAR(20) NOT NULL DEFAULT 'INDIVIDUAL', -- INDIVIDUAL | FAMILIAR
 codigo_invitacion VARCHAR(10) UNIQUE,
 fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE gastos.usuarios ADD COLUMN IF NOT EXISTS cuenta_id INTEGER REFERENCES gastos.cuentas(id);
ALTER TABLE gastos.usuarios ADD COLUMN IF NOT EXISTS rol_cuenta VARCHAR(20) DEFAULT 'ADMIN'; -- ADMIN | MIEMBRO

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

CREATE TABLE IF NOT EXISTS gastos.planes (
 id SERIAL PRIMARY KEY,
 slug VARCHAR(30) UNIQUE NOT NULL,
 nombre VARCHAR(100) NOT NULL,
 tipo_cuenta VARCHAR(20) NOT NULL, -- INDIVIDUAL | FAMILIAR
 precio_centavos INTEGER NOT NULL,
 limite_miembros INTEGER NOT NULL DEFAULT 1,
 stripe_price_id VARCHAR(100),
 activo BOOLEAN DEFAULT TRUE
);

INSERT INTO gastos.planes (slug, nombre, tipo_cuenta, precio_centavos, limite_miembros, stripe_price_id)
VALUES
 ('basico', 'Básico', 'INDIVIDUAL', 1000, 1, 'price_PENDIENTE_BASICO'),
 ('individual', 'Individual', 'INDIVIDUAL', 4900, 1, 'price_PENDIENTE_INDIVIDUAL'),
 ('familiar', 'Familiar', 'FAMILIAR', 9900, 5, 'price_PENDIENTE_FAMILIAR')
ON CONFLICT (slug) DO NOTHING;

-- Una fila por cuenta con su estado de pago. status sigue el
-- vocabulario de Stripe: incomplete | trialing | active | past_due
-- | canceled. plan_id y los campos stripe_* se llenan cuando el
-- webhook confirma el pago (ver webhook_service/).

CREATE TABLE IF NOT EXISTS gastos.suscripciones (
 id SERIAL PRIMARY KEY,
 cuenta_id INTEGER NOT NULL REFERENCES gastos.cuentas(id),
 plan_id INTEGER REFERENCES gastos.planes(id),
 stripe_customer_id VARCHAR(100),
 stripe_subscription_id VARCHAR(100),
 status VARCHAR(30) NOT NULL DEFAULT 'incomplete',
 fecha_inicio TIMESTAMP,
 fin_periodo_actual TIMESTAMP,
 cancelar_al_final_periodo BOOLEAN DEFAULT FALSE,
 fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_suscripciones_cuenta ON gastos.suscripciones(cuenta_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_suscripciones_stripe_sub
 ON gastos.suscripciones(stripe_subscription_id)
 WHERE stripe_subscription_id IS NOT NULL;
