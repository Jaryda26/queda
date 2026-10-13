-- Periodos de calendario (corre UNA vez en el SQL Editor de Supabase).
-- Guarda el día en que inicia tu semana (0=lunes ... 4=viernes ... 6=domingo).
ALTER TABLE gastos.presupuestos
  ADD COLUMN IF NOT EXISTS dia_inicio INTEGER DEFAULT 0;
