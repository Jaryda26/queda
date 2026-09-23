# Fase 2 — Saludo interactivo con IA y proyección financiera

## Qué se agregó

**`services/narrativa_service.py`** — el motor nuevo. Hace dos cosas
separadas a propósito:

1. `calcular_datos_proyeccion(uid)` — 100% Python, sin IA. Calcula:
   - Tu ritmo de gasto diario dentro del periodo de presupuesto activo
     (gasto acumulado del periodo ÷ días transcurridos).
   - Proyección de cierre de periodo: si mantienes ese ritmo, ¿terminas
     con margen o con déficit, y de cuánto?
   - Tu próximo recordatorio pendiente (el más próximo por fecha,
     cualquier descripción/frecuencia — no está atado a "viernes").
   - Proyección específica a la fecha de ese recordatorio: si sigues
     al mismo ritmo, ¿vas a tener para cubrirlo y con cuánto sobra/falta?

2. `generar_narrativa_ia(uid)` — toma esos datos ya calculados (la
   fuente de verdad) y le pide a la IA (Azure OpenAI, mismo modelo que
   ya usa el Asistente) que solo los redacte con tono cálido o de
   alerta amable, según corresponda. La IA tiene prohibido por prompt
   inventar o modificar cifras — solo redacta con los números que le
   mandamos.
   - **Si la IA falla por cualquier motivo** (sin credenciales, sin
     internet, cuota agotada) cae automáticamente a
     `_narrativa_plantilla()`, que arma el mismo mensaje con plantillas
     de texto usando los mismos datos. El saludo nunca se cae ni se
     queda en blanco.

**`services/ai_client.py`** — cliente de Azure OpenAI centralizado y
de inicialización perezosa (antes vivía hardcodeado en
`views/asistente.py` y se creaba al importar el módulo, así que la
app completa podía tronar al arrancar si faltaban las credenciales,
aunque nunca visitaras esa pantalla). Ahora `asistente.py` y
`narrativa_service.py` comparten el mismo cliente.

## Cómo se conectó

`views/home.py`:
- Se eliminó `obtener_resumen()` y la vieja `generar_narrativa()`
  (plantilla fija sin proyección) — quedaron reemplazadas por
  `generar_narrativa_ia(uid)`.
- El mensaje se sigue mostrando con `st.success()` y reproduciendo
  por voz igual que antes (`texto_a_voz`), una sola vez por sesión.

## Ejemplo de lo que ahora puede decir

> "Vas muy bien, Jorge. A tu ritmo actual vas a cerrar el periodo con
> $850 de margen. Tu próximo pendiente es Renta ($3,500), vence en 4
> días — si sigues así, para entonces te van a sobrar $200."

o en el caso contrario:

> "Ojo: a tu ritmo actual cerrarías el periodo $400 arriba de tu
> presupuesto. Tu próximo pendiente es Tarjeta ($1,200), vence mañana
> — si sigues así, te faltarían $150 para cubrirla."

## Pendiente / ideas para seguir puliendo
- Ahora mismo la narrativa se genera cada vez que entras a Inicio en
  una sesión nueva (una llamada a OpenAI por sesión, no por cada
  rerun — está bien para uso personal; si esto se vuelve multiusuario
  en un SaaS, vale la pena cachear por día para no pagar una llamada
  por cada login).
- Se podría extender el mismo `calcular_datos_proyeccion()` para
  alimentar también el Dashboard (hoy el Dashboard sigue usando su
  propio cálculo, sin proyección).
