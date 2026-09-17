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
 usuario_id INTEGER,
 fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 tipo VARCHAR(20),
 concepto VARCHAR(255),
 categoria VARCHAR(100),
 monto NUMERIC(12,2),
 texto_original TEXT
);
