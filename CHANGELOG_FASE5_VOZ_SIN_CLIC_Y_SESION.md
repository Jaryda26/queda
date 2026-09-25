# Fase 5 — Activación por voz sin clic, nombre del agente, sesión persistente

## 1. Activación por voz diciendo el nombre (nivel 1 + wake-word)

Nuevo componente `components/mic_wakeword/` — HTML/JS que corre en el
navegador usando la **Web Speech API nativa** (no Azure): escucha el
micrófono de forma continua y solo manda texto a Python cuando
detecta que dijiste el nombre elegido, funcionando en dos formas:

- "Queda, cuánto llevo gastado" — todo en una frase.
- "Queda" ... (pausa) ... "cuánto llevo gastado" — como Alexa: el
  nombre activa la escucha, la siguiente frase es el comando.

Se corta sola al terminar de hablar (nivel 1: no hay que dar clic
para parar) y se reactiva sola después de cada comando.

**Limitación real, no oculto nada:** la Web Speech API solo existe en
Chrome, Edge y Safari — **no funciona en Firefox**. Por eso lo dejé
como interruptor apagado por default ("🗣️ Activación por voz (beta)"
en la barra lateral) — el micrófono de siempre (clic para grabar,
vía Azure Speech) sigue funcionando igual, en todos los navegadores,
sin tocarlo.

`views/voz.py` se partió en dos: `procesar_texto_voz(texto)` (toda
la lógica de siempre — esperando monto, reglas, IA) ahora es
compartida por el camino de audio (Azure) y el camino de texto
(wake-word del navegador), en vez de duplicarse.

## 2. Nombre personalizado del agente

Columna nueva `usuarios.nombre_agente` (default "Queda"). Cada quien
elige el suyo en 👨‍👩‍👧 Mi cuenta → "Nombre de tu asistente" — se
guarda por usuario (en una cuenta Familiar, cada miembro puede
ponerle un nombre distinto si quiere) y es la palabra que activa el
micrófono del punto 1.

## 3. Sesión persistente ("recuérdame")

Antes, Streamlit borraba la sesión cada vez que se reabría la
pestaña — tenías que loguearte de nuevo. Ahora, al iniciar sesión se
guarda un token en una cookie del navegador (30 días), y si vuelves
sin sesión activa pero con esa cookie válida, entras directo sin
pedir contraseña.

Detalles de seguridad, ya que esto toca autenticación:
- El token es aleatorio (`secrets.token_urlsafe(32)`, 256 bits) —
  no es algo adivinable.
- En la base **nunca se guarda el token en claro**, solo su hash
  sha256 (`usuarios.token_sesion_hash`) — igual que una contraseña,
  aunque con sha256 en vez de bcrypt (no hace falta que sea lento,
  es aleatorio, no algo que alguien intente adivinar por fuerza
  bruta con un diccionario).
- "Cerrar Sesión" ahora invalida el token en la base (no solo borra
  la cookie) — así, si alguien más tuviera copiada esa cookie vieja,
  deja de servirle también.
- Paquete usado: `extra-streamlit-components` (`CookieManager`) —
  ya validado que existe en PyPI y se importa sin problemas antes de
  usarlo.

## Validado

`py_compile` + `pyflakes` sobre todo el árbol (incluyendo el
componente nuevo) — 0 errores. La librería de cookies se instaló y
se confirmó que importa correctamente.

## Pendiente de que tú pruebes (no lo puedo probar yo, necesita
## navegador real)

- Que la activación por voz sí escuche bien en tu Chrome/Edge real
  (el comportamiento exacto de reinicio automático de
  `SpeechRecognition` varía un poco entre navegadores).
- Que la sesión persistente sobreviva cerrar/reabrir la pestaña como
  esperas — `CookieManager` a veces necesita un primer render "en
  blanco" antes de tener la cookie disponible (es normal de la
  librería, se resuelve solo en el siguiente rerun).
