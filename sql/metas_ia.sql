-- Metas de ahorro + contador diario de IA
-- Corre esto UNA vez en el SQL Editor de Supabase. Seguro de repetir.

-- Metas de ahorro (compartidas por la cuenta; todos los planes).
CREATE TABLE IF NOT EXISTS gastos.metas_ahorro (
 id SERIAL PRIMARY KEY,
 cuenta_id INTEGER NOT NULL REFERENCES gastos.cuentas(id),
 usuario_id INTEGER REFERENCES gastos.usuarios(id),
 nombre VARCHAR(80) NOT NULL,
 monto_objetivo NUMERIC(14,2) NOT NULL,
 ahorrado NUMERIC(14,2) NOT NULL DEFAULT 0,
 fecha_limite DATE,
 completada BOOLEAN NOT NULL DEFAULT FALSE,
 fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_metas_cuenta ON gastos.metas_ahorro(cuenta_id);

-- Cada abono (o retiro, con monto negativo) a una meta.
CREATE TABLE IF NOT EXISTS gastos.abonos_meta (
 id SERIAL PRIMARY KEY,
 meta_id INTEGER NOT NULL REFERENCES gastos.metas_ahorro(id) ON DELETE CASCADE,
 cuenta_id INTEGER NOT NULL REFERENCES gastos.cuentas(id),
 usuario_id INTEGER REFERENCES gastos.usuarios(id),
 monto NUMERIC(14,2) NOT NULL,
 fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_abonos_meta ON gastos.abonos_meta(meta_id);

-- Uso diario de IA por cuenta (para el límite según el plan).
CREATE TABLE IF NOT EXISTS gastos.uso_ia (
 cuenta_id INTEGER NOT NULL REFERENCES gastos.cuentas(id),
 dia DATE NOT NULL,
 usos INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY (cuenta_id, dia)
);
