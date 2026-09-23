# Fase 1 — Bugs y seguridad (Queda)

## 🔴 Críticos
- **Inyección SQL en login** (`services/usuario_service.py`): el email se
  interpolaba directo en el `SELECT` (`f"...where email='{e}'"`). Un
  correo como `' OR '1'='1` bastaba para saltarse el login. Ahora usa
  parámetros (`:email`) en login y registro.
- **`views/movimientos.py` roto**: usaba la variable `m`, que no existía
  → `NameError` al dar clic en "Guardar Movimiento". El módulo estaba
  100% inutilizable. Corregido y con validación de campos vacíos.
- **Asistente de texto roto para el caso de uso principal**
  (`views/asistente.py`): `detectar_intencion()` regresa `None` a propósito
  para frases de gasto/ingreso normales (para dejarlas pasar a OpenAI),
  pero el código hacía `intencion["accion"]` sin checar `None` primero.
  Resultado: escribir "Compré una coca de 25 pesos" (el ejemplo que la
  propia pantalla sugiere) tronaba con error en cada intento. Corregido,
  y de paso eliminé un bloque de código muerto (líneas después de un
  `return` que nunca se ejecutaban).
- **`sql/schema.sql` incompleto**: faltaban las tablas `gastos.recordatorios`
  y `gastos.diccionario_usuario` (usadas por el código pero nunca creadas),
  y las columnas `movimientos.origen_ingreso` y `presupuestos.fecha_creacion`
  (referenciadas en varias vistas). Si alguien monta la base desde cero con
  este script, la app truena en Recordatorios, Aprendizaje, Historial y
  Presupuesto. Agregado todo con `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`
  — es seguro correrlo sobre tu base actual.

## 🟡 Funcionales
- **Recordatorios recurrentes nunca avanzaban de fecha**: al marcar "Pagado"
  un recordatorio SEMANAL/QUINCENAL/MENSUAL/ANUAL, solo se actualizaba
  `fecha_ultimo_pago`, nunca `fecha_vencimiento` — se quedaba "vencido"
  para siempre. Mismo bug estaba duplicado en `home.py`, `recordatorios.py`
  y en el flujo de voz "ya quedó X" (`action_engine.py`). Centralicé la
  lógica en `services/recordatorios_service.py::marcar_pagado()`, que
  calcula bien el siguiente periodo (incluye manejo de fin de mes/año).
- **`speech_service.py`**: cuando Azure no reconocía el audio devolvía el
  string `"NO_MATCH"` (truthy en Python), así que `if not texto:` en
  `voz.py` nunca detectaba el fallo y se mandaba "NO_MATCH" como si fuera
  texto real al motor de intención/OpenAI. Ahora regresa `None` en todos
  los casos de fallo.

## 🟢 Endurecimiento (defensa en profundidad)
- Todas las queries que armaban `WHERE usuario_id={uid}` con f-strings
  (en `home.py`, `dashboard.py`, `historial.py`, `presupuesto.py`,
  `recordatorios.py`, `aprendizaje.py`, `action_engine.py`, `asistente.py`)
  ahora usan parámetros (`:uid`). Antes no eran explotables porque `uid`
  viene de `session_state` (un int puesto por el login), pero es la
  práctica correcta y evita que un cambio futuro (ej. exponer `uid` en la
  URL) abra la puerta a inyección.
- `db.py::obtener_dataframe()` ahora acepta `params`, igual que
  `ejecutar_query()`.

## 🧹 Limpieza
- Eliminé `home_real.py` y `home_real.txt` (versiones viejas de `home.py`
  que ya nadie importaba) y las carpetas `__pycache__`.
- Verificado con `py_compile` + `pyflakes`: el proyecto completo compila
  sin errores ni variables indefinidas.

## 📌 Notas para la siguiente fase (no tocado todavía)
- Encontré `BASE/TABLAS.txt` con un borrador de tablas para
  `gastos.suscripciones` y `gastos.configuracion_usuario` — ya habías
  empezado a pensar en el modelo de suscripción. Lo voy a retomar cuando
  ataquemos la fase de cobros/planes.
- `.env` ya está en `.gitignore`, así que no debería llegar a tu repo.

---

# Fix adicional — Menú lateral no respondía al mouse

**Síntoma:** solo se podía cambiar de pantalla por voz; el clic en el
menú de la barra lateral no hacía nada.

**Causa** (`app.py`): el bloque "Sincronización automática" (pensado
para que el radio del menú reflejara los cambios hechos por voz) se
ejecutaba *antes* de dibujar el radio button, comparando
`menu_principal` (que Streamlit ya había actualizado con tu clic)
contra `pagina_actual` (que todavía no se había actualizado). Como
diferían, el bloque asumía que había que "resincronizar" y pisaba tu
clic, devolviendo el radio a la página anterior antes de que se
alcanzara a procesar.

**Fix:** reemplacé esa comparación por una variable de control
(`pagina_sincronizada`) que guarda la última página que ya quedó
reflejada en el radio. Solo se fuerza el radio cuando `pagina_actual`
cambió *por fuera* del propio widget (es decir, por voz) — un clic
manual ya no se pisa. De paso quedó sin uso la bandera
`debug_accion` que se usaba para este mismo propósito; la dejé
inicializada (no rompe nada) pero ya no se lee en ningún lado —
es candidata a limpieza en la siguiente pasada.
