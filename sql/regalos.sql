-- Códigos de regalo / pruebas (corre esto UNA vez en el SQL Editor de Supabase).
-- Seguro de repetir: todo es IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS gastos.codigos_regalo (
 id SERIAL PRIMARY KEY,
 codigo VARCHAR(30) NOT NULL,
 dias INTEGER NOT NULL DEFAULT 30,
 plan_slug VARCHAR(30) NOT NULL DEFAULT 'individual',
 usos_max INTEGER NOT NULL DEFAULT 1,
 usos INTEGER NOT NULL DEFAULT 0,
 vence TIMESTAMP,
 activo BOOLEAN NOT NULL DEFAULT TRUE,
 nota VARCHAR(200),
 creado_por INTEGER REFERENCES gastos.usuarios(id),
 fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_codigos_regalo_codigo
 ON gastos.codigos_regalo(codigo);

-- Quién canjeó qué (una cuenta no puede canjear el mismo código dos veces).
CREATE TABLE IF NOT EXISTS gastos.canjes_regalo (
 id SERIAL PRIMARY KEY,
 codigo_id INTEGER NOT NULL REFERENCES gastos.codigos_regalo(id),
 cuenta_id INTEGER NOT NULL REFERENCES gastos.cuentas(id),
 usuario_id INTEGER REFERENCES gastos.usuarios(id),
 fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_canjes_codigo_cuenta
 ON gastos.canjes_regalo(codigo_id, cuenta_id);
