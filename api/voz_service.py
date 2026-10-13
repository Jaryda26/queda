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
from services.plan_ia_service import resolver_texto_libre

log = logging.getLogger("queda.voz")

# pagina_actual de la web -> pestaña de la app móvil (None = solo web)
_DESTINOS = {
    "inicio": "dashboard",
    "dashboard": "dashboard",
    "movimientos": "movimientos",
    "historial": "movimientos",
    "recordatorios": "recordatorios",
    "presupuesto": "presupuesto",
    "aprendizaje": "aprendizaje",
    "metas de ahorro": "metas",
    "asistente ia": "asesor",
}

_SOLO_WEB = {
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
    ).ratio() < 0.8:
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


_INICIO_REGISTRO = re.compile(
    r"^(?:(?:ya|hoy|ayer|antier|anteayer|oye|mira|pues)\s+)*"
    r"(?:gaste|compre|pague|cobre|gane|recibi|vendi|me cobraron|me costo|"
    r"me costaron|me depositaron|me transfirieron|me pagaron|se me fueron)\b"
)


def _parece_registro(texto):
    from services.intent_engine import normalizar_texto
    return bool(_INICIO_REGISTRO.match(normalizar_texto(texto)))


def _asesor_chat(cuenta_id, texto, plan, historial):
    """Pregunta abierta al asesor: IA si el plan la incluye y hay cupo; si
    no, la versión calculada (siempre responde algo útil)."""

    from services.asesor_service import asesor_ia, respuesta_calculada
    from services.plan_ia_service import (
        consumir_ia,
        devolver_ia,
        mensaje_limite_alcanzado,
    )

    try:
        base = respuesta_calculada(cuenta_id, texto)
    except Exception:
        log.exception("Falló el cálculo del asesor")
        base = "No pude calcular tus números ahora mismo."

    if plan is None or not plan.get("incluye_ia", False):
        return (
            base + "\n\nCon el plan Individual o Familiar el asesor "
            "analiza tus movimientos con inteligencia artificial y "
            "responde cualquier pregunta."
        )

    permitido, _, limite = consumir_ia(cuenta_id, plan)

    if not permitido:
        return base + "\n\n" + mensaje_limite_alcanzado(limite, plan)

    try:
        return asesor_ia(cuenta_id, texto, historial)
    except Exception:
        devolver_ia(cuenta_id)
        log.exception("Falló el asesor con IA")
        return base + "\n\n(La IA no respondió; esto es calculado y no gastó tu cupo.)"


def procesar(usuario, texto, esperando_monto=False, modo_chat=False, historial=None):

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

    # ---- texto libre: reglas simples, y IA si el plan la incluye ----
    cuenta_id = int(usuario["cuenta_id"])
    plan = obtener_plan_actual(cuenta_id)

    # En el chat del asesor, lo que no parece un registro es una pregunta
    # para el asesor (consejos, diagnóstico, inversión...).
    if modo_chat and not _parece_registro(texto):
        return _resultado(
            "MENSAJE", _asesor_chat(cuenta_id, texto, plan, historial),
            texto=texto,
        )

    tipo_r, valor = resolver_texto_libre(cuenta_id, texto, plan)

    if tipo_r == "BLOQUEO":
        return _resultado("ERROR", valor, texto=texto)

    intencion = valor
    intencion["texto_original"] = texto

    tipo, mensaje, nav = _ejecutar(intencion, estado)

    return _resultado(
        tipo, mensaje, nav,
        esperando_monto=bool(estado.get("esperando_monto_ingreso")),
        texto=texto,
    )
