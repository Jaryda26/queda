# Fase 4 — Recordatorios por voz + Rediseño visual

## Recordatorios por voz/texto

Ahora puedes crear recordatorios hablando o escribiendo, igual que
ya funcionaba con gastos/ingresos:

> "Recuérdame pagar la tarjeta Sears el próximo viernes por 1300 pesos"
> "Ponme un recordatorio mensual de la renta, 3500 pesos, cada día 5"

Cómo quedó armado:
- **`views/asistente.py`**: el prompt de la IA ahora incluye
  `CREAR_RECORDATORIO` como acción válida, con ejemplos. Le mando a
  la IA la fecha de HOY (con día de la semana) en cada llamada, para
  que pueda resolver fechas relativas ("el viernes", "en 3 días",
  "cada día 5") a una fecha real — antes no tenía ese contexto.
- **`services/action_engine.py`**: nuevo manejador para
  `CREAR_RECORDATORIO` — valida descripción/fecha, convierte la
  fecha de texto a un `date` real (con mensaje de error claro si la
  IA manda algo mal formado en vez de tronar), respeta el tope de
  recordatorios del plan, e inserta.
- **`services/recordatorios_service.py`**: factoricé
  `puede_agregar_recordatorio()` (antes esa lógica solo vivía
  duplicada en el formulario manual) para que la compartan el
  formulario y la creación por voz — un solo lugar donde vive la
  regla del tope.

**Importante:** esto usa el mismo motor de IA que ya usa el
Asistente, así que solo está disponible en planes Individual y
Familiar (igual que el resto del Asistente IA) — en Básico, los
comandos de voz para navegar y para "ya pagué X" / "después X"
siguen funcionando igual (no usan IA), pero crear un recordatorio
nuevo por voz libre no.

## Rediseño visual

- **`.streamlit/config.toml`**: nueva paleta — verde azulado/esmeralda
  (`#0F9D8B`) en vez del verde genérico de Streamlit por defecto,
  con texto en un gris verdoso oscuro en vez de negro puro.
- **`services/ui_theme.py`** (nuevo, se llama una vez desde
  `app.py`): tipografía Inter vía Google Fonts, sidebar con fondo
  verde oscuro sólido y botones con su propio estilo, tarjetas
  (`st.container(border=True)`) con esquinas más redondeadas y
  sombra sutil, botones con animación al pasar el mouse, inputs con
  esquinas redondeadas, títulos más marcados.
- **`views/home.py`**: la pantalla de Inicio ahora abre con 3
  métricas (💰 Disponible, 📈 Proyección del periodo, 🔔
  Recordatorios pendientes) antes del mensaje de bienvenida, en vez
  de solo texto — más "dashboard", menos "wall of text". Reutiliza
  los mismos datos que ya calculaba la narrativa (no duplica
  consultas a la base: `generar_narrativa_ia()` ahora acepta un
  parámetro `datos` opcional para esto).

Los selectores CSS usan atributos `data-testid` de Streamlit
(`stSidebar`, `stVerticalBlockBorderWrapper`, `stMetricValue`,
`stAlert`), que son más estables entre versiones que las clases
autogeneradas — pero si una versión futura de Streamlit cambia su
HTML interno, en el peor caso el estilo deja de aplicarse (degrada
con gracia) sin romper ninguna funcionalidad.

## Validado

`py_compile` + `pyflakes` sobre todo el árbol — 0 errores.
