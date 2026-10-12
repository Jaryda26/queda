"""
Cerebro de voz para el celular. Es el MISMO flujo que views/voz.py de la
web (nombre del agente -> monto pendiente -> frases de Aprendizaje ->
reglas -> IA), pero sin Streamlit: recibe el texto que el teléfono ya
transcribió y regresa un resultado estructurado.
"""

import difflib
import logging
import re

from services.action_engine import ejecutar_accion
from services.aprendizaje_service import buscar_frase_aprendida
from services.billing_service import obtener_plan_actual
from services.estado_voz import nueva_sesion, NavegarSolicitado
from services.intent_engine import detectar_intencion, extraer_monto_de_texto
from services.interprete_ia import interpretar_movimiento

log = logging.getLogger("queda.voz")

# pagina_actual de la web -> pestaña de la app móvil (None = solo web)
_DESTINOS = {
    "inicio": "dashboard",
    "dashboard": "dashboard",
    "movimientos": "movimientos",
    "historial": "movimientos",
    "recordatorios": "recordatorios",
}

_SOLO_WEB = {
    "presupuesto": "Presupuesto",
    "aprendizaje": "Aprendizaje",
    "asistente ia": "Asistente",
    "cuenta": "Cuenta",
    "suscripcion": "Suscripción",
}

_BASURA_VOZ = re.compile(
    "[\U00010000-\U0010ffff☀-➿⬀-⯿️‍]"
)


def _monto_hablado(numero):
    """'12,000.00' -> '12000 pesos' ; '350.50' -> '350 pesos con 50 centavos'."""
    limpio = numero.replace(",", "")
    entero, _, dec = limpio.partition(".")
    dec = (dec + "00")[:2]
    texto = f"{int(entero or 0)} pesos"
    if dec != "00":
        texto += f" con {int(dec)} centavos"
    return texto


def texto_para_voz(mensaje):
    """Quita emojis y markdown para que el TTS del teléfono no los lea."""
    t = mensaje or ""
    # "$12,000.00" -> "12000 pesos" (el TTS del teléfono lo leía como dólares)
    t = t.replace("\\", "")
    t = re.sub(
        r"\$\s*([\d,]+(?:\.\d+)?)(\s*pesos)?",
        lambda m: _monto_hablado(m.group(1)),
        t,
    )
    t = _BASURA_VOZ.sub("", t)
    t = t.replace("**", "").replace("`", "").replace("*", "")
    t = re.sub(r"\n{2,}", ". ", t)
    t = t.replace("\n", " ")
    return re.sub(r"\s+", " ", t).strip()


def _quitar_nombre_agente(texto, nombre_agente):
    """Igual que la web: 'Trobi, cuánto llevo' -> 'cuánto llevo' (tolerante)."""

    nombre = (nombre_agente or "").strip()
    palabras = texto.strip().split()

    if not nombre or not palabras:
        return texto

    primera = re.sub(r"[^\wáéíóúñü]", "", palabras[0], flags=re.IGNORECASE)

    if difflib.SequenceMatcher(
        None, primera.lower(), nombre.lower()
    ).ratio() < 0.6:
        return texto

    resto = re.sub(r"^[,.:;!?]+\s*", "", " ".join(palabras[1:]).strip())
    return resto


def _resultado(tipo, mensaje, navegar=None, esperando_monto=False, texto=""):
    return {
        "tipo": tipo,                      # MENSAJE | ERROR | NAVEGACION
        "mensaje": mensaje,                # para mostrar
        "voz": texto_para_voz(mensaje),    # para que el teléfono lo diga
        "navegar": navegar,                # dashboard|movimientos|recordatorios|None
        "esperando_monto": esperando_monto,
        "texto_reconocido": texto,
        "refrescar": tipo == "MENSAJE" and not esperando_monto,
    }


def _ejecutar(intencion, estado):
    """Corre ejecutar_accion; un st.rerun() de navegación se vuelve destino."""

    try:
        mensaje = ejecutar_accion(intencion)
    except NavegarSolicitado:
        pagina = re.sub(
            r"^[^\w]+", "", str(estado.get("pagina_actual") or "")
        ).strip().lower()
        pagina = pagina.replace("í", "i").replace("ó", "o")

        destino = _DESTINOS.get(pagina)

        if destino:
            return "NAVEGACION", f"Abriendo {destino}", destino

        nombre = next(
            (v for k, v in _SOLO_WEB.items() if k in pagina), pagina
        )
        return (
            "MENSAJE",
            f"{nombre} por ahora solo está disponible en la web.",
            None,
        )

    if not mensaje:
        return "ERROR", "No entendí qué hacer con eso. Intenta decirlo de otra forma.", None

    return "MENSAJE", str(mensaje), None


def procesar(usuario, texto, esperando_monto=False):

    estado = nueva_sesion(
        user_id=int(usuario["id"]),
        cuenta_id=int(usuario["cuenta_id"]),
        esperando_monto_ingreso=False,
        pagina_actual=None,
    )

    texto = (texto or "").strip()

    if not texto:
        return _resultado("ERROR", "No escuché nada. Intenta de nuevo.")

    # ---- nombre del agente ("Trobi, ...") ----
    sin_nombre = _quitar_nombre_agente(texto, usuario.get("nombre_agente"))

    if sin_nombre != texto:
        if not sin_nombre:
            return _resultado("MENSAJE", "Te escucho, ¿qué necesitas?", texto=texto)
        texto = sin_nombre

    # ---- respuesta a "¿cuál fue el monto?" ----
    if esperando_monto:

        monto = extraer_monto_de_texto(texto)

        if monto is None:
            return _resultado(
                "ERROR",
                "No logré identificar el monto. Dime solo la cantidad, "
                "por ejemplo 12000 pesos.",
                esperando_monto=True,
                texto=texto,
            )

        tipo, mensaje, nav = _ejecutar({
            "accion": "REGISTRAR_INGRESO",
            "concepto": "Ingreso",
            "origen_ingreso": "Ingreso",
            "monto": monto,
            "texto_original": texto,
        }, estado)

        return _resultado(tipo, mensaje, nav, texto=texto)

    # ---- frases de Aprendizaje > reglas de fábrica ----
    intencion = buscar_frase_aprendida(int(usuario["cuenta_id"]), texto)

    if intencion is None:
        intencion = detectar_intencion(texto)

    if intencion:

        intencion["texto_original"] = texto

        tipo, mensaje, nav = _ejecutar(intencion, estado)

        return _resultado(
            tipo, mensaje, nav,
            esperando_monto=bool(estado.get("esperando_monto_ingreso")),
            texto=texto,
        )

    # ---- IA (solo planes con IA) ----
    plan = obtener_plan_actual(int(usuario["cuenta_id"]))

    if plan is None or not plan.get("incluye_ia", True):
        return _resultado(
            "ERROR",
            "Registrar por voz libre requiere el plan Individual o "
            "Familiar. Puedes usar comandos como abre el dashboard o "
            "ya pagué y el nombre del recordatorio.",
            texto=texto,
        )

    try:
        intencion = interpretar_movimiento(texto)
    except Exception as e:
        log.exception("Falló la interpretación con IA")
        # Sin datos sensibles: solo el TIPO de falla, para poder diagnosticar.
        causa = type(e).__name__
        if isinstance(e, (KeyError, RuntimeError)):
            causa = "faltan credenciales AZURE_OPENAI en el servidor"
        return _resultado(
            "ERROR",
            f"No pude interpretar eso ahora mismo (IA: {causa}).",
            texto=texto,
        )

    intencion["texto_original"] = texto

    tipo, mensaje, nav = _ejecutar(intencion, estado)

    return _resultado(
        tipo, mensaje, nav,
        esperando_monto=bool(estado.get("esperando_monto_ingreso")),
        texto=texto,
    )
