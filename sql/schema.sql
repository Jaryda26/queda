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
