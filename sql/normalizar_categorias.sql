-- Limpieza de categorías (corre UNA vez en el SQL Editor de Supabase).
-- 1) "COMIDA" y "Comida" pasan a ser la misma categoría.
-- 2) Los pagos de recordatorios que quedaron como "Recordatorio" se
--    reclasifican según su concepto (Deudas, Servicios, etc.).

BEGIN;

-- 1) Unificar mayúsculas/minúsculas y espacios.
UPDATE gastos.movimientos
SET categoria = INITCAP(TRIM(categoria))
WHERE categoria IS NOT NULL
  AND categoria <> INITCAP(TRIM(categoria));

UPDATE gastos.movimientos SET categoria = 'Otros'
WHERE categoria IS NULL OR TRIM(categoria) = '' OR categoria ILIKE 'sin categor%';

-- 2) Reclasificar "Recordatorio" por concepto.
UPDATE gastos.movimientos
SET categoria = CASE
  WHEN concepto ~* '(tarjeta|banco|bbva|bancomer|banorte|santander|hsbc|banamex|citi|scotia|inbursa|bajio|afirme|banregio|azteca|credito|crédito|prestamo|préstamo|hipoteca|financiamiento|credileasing|sears|coppel|liverpool|mercado pago|nu bank|nubank|klar|amex|visa|mastercard|deuda|adeudo)' THEN 'Deudas'
  WHEN concepto ~* '(luz|cfe|agua|gas|internet|telmex|izzi|totalplay|telefono|teléfono|celular|renta|predial|mantenimiento)' THEN 'Servicios'
  WHEN concepto ~* '(netflix|spotify|disney|prime|hbo|cine|youtube)' THEN 'Entretenimiento'
  WHEN concepto ~* '(gasolina|pemex|combustible)' THEN 'Gasolina'
  WHEN concepto ~* '(doctor|medico|médico|hospital|farmacia|dentista)' THEN 'Salud'
  ELSE 'Otros'
END
WHERE categoria = 'Recordatorio';

COMMIT;

-- Revisa el resultado:
-- SELECT categoria, COUNT(*), SUM(monto) FROM gastos.movimientos
-- WHERE tipo='GASTO' GROUP BY categoria ORDER BY 3 DESC;
