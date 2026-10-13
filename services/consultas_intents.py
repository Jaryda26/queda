"""
Frases de CONSULTA (calculadas, sin IA) y de METAS DE AHORRO.
Se revisan al inicio de detectar_intencion(), porque palabras como
"presupuesto" o "gastos" las confundiría con comandos de navegación.
"""

import re

from services.intent_engine import (
    detectar_categoria,
    extraer_monto_flexible,
    normalizar_texto,
)

_CATEGORIAS_DIRECTAS = {
    "gasolina": "Gasolina",
    "comida": "Comida",
    "comidas": "Comida",
    "servicios": "Servicios",
    "transporte": "Transporte",
    "salud": "Salud",
    "entretenimiento": "Entretenimiento",
    "otros": "Otros",
}

_RE_GASTO_MAYOR = re.compile(
    r"\b(en que (he )?gast\w* mas|en que gasto mas|en que se me va|"
    r"donde se me va|donde gasto mas|donde he gastado mas|"
    r"que es lo que mas gasto|mayores gastos|mayor gasto|"
    r"gastos mas grandes|gastos mas altos|en que estoy gastando mas|"
    r"en que gaste mas|que gasto mas)\b"
)

_RE_AFECTA = re.compile(
    r"(afect\w+ .*presupuesto|presupuesto .*afect\w+|"
    r"\bpor que (no me alcanza|se me acaba|se me va|voy mal|me pase|"
    r"me estoy pasando|se acaba)|"
    r"\bque (me )?esta (pesando|pegando|golpeando|afectando)|"
    r"\bque esta pesando)"
)

_RE_CUANTO_LLEVO = re.compile(
    r"(cuanto (llevo|he gastado|he usado|me queda|me sobra|ha avanzado) "
    r"(del|de mi|de el|en mi|a mi) presupuesto|"
    r"como (va|vamos|voy con) (mi |el )?presupuesto|"
    r"cuanto (puedo|podria) gastar (al dia|por dia|diario|hoy)|"
    r"cuanto me queda para (gastar|el (mes|periodo|resto))|"
    r"que tanto (llevo|he usado) (de mi )?presupuesto|"
    r"estado de mi presupuesto)"
)

_RE_CUANTO_GASTE = re.compile(r"\bcuanto (he )?(gast\w+)\b(.*)")

_RE_CONSEJO = re.compile(
    r"\b(dame (un |algun |unos )?(consejo|consejos|tip|tips|recomendacion|"
    r"recomendaciones)|"
    r"(un |algun )?consejo(s)?( personal(es)?)?$|"
    r"como (puedo |podria )?(ahorrar|ahorro|mejorar mis finanzas|"
    r"gastar menos|controlar mis gastos)|"
    r"que me recomiendas|ayudame a ahorrar|como (le )?hago para ahorrar|"
    r"en que puedo (ahorrar|recortar|gastar menos)|"
    r"donde puedo (ahorrar|recortar)|que (puedo|debo) recortar)\b"
)

# ---- metas ----

_RE_ABRIR_METAS = re.compile(
    r"\b(abre|abrir|ve a|ir a|muestrame|llevame a|ensename)\s+(mis |las |la )?"
    r"(metas|meta de ahorro|metas de ahorro)\b"
)

_RE_CREAR_META = re.compile(
    r"(?:^|\b)(?:(?:quiero|quisiera|necesito|voy a|vamos a|me gustaria|"
    r"pretendo|planeo)\s+ahorrar|(?:crea|crear|nueva|agrega|agregar|pon|"
    r"anade|abre|haz)\s+(?:una |otra )?(?:nueva )?meta(?: de ahorro)?|"
    r"mi meta (?:es|sera) ahorrar|mi nueva meta)\b"
)

_RE_PLAZO = re.compile(
    r"\ben (\d+|un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|"
    r"once|doce) (dias?|semanas?|meses|mes|anos?)\b"
)

_PLAZO_PALABRA = {
    "un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12,
}

_RE_ABONO = re.compile(
    r"^(?:ya |quiero |quisiera |voy a |necesito |favor de |oye |"
    r"ahora |pues )*(?:abon\w+|aport\w+|ahorre|guarde|guardar|guarda|"
    r"apart\w+)\b"
)

_RE_ABONO_AMBIGUO = re.compile(
    r"^(?:ya |quiero |quisiera |voy a |necesito |favor de |oye |"
    r"ahora |pues )*(?:agrega\w*|mete\w*|deposita\w*|suma\w*|"
    r"anade\w*|pon\w*|echa\w*)\b"
)

_RE_RETIRO = re.compile(
    r"^(?:ya |quiero |quisiera |voy a |necesito |oye |ahora |pues )*"
    r"(?:retir\w+|saque|saca\w*|quita\w*|descuenta\w*)\b"
)

_RE_CONSULTAR_METAS = re.compile(
    r"(\b(como|cuanto) (van|voy|vamos|llevo|me falta|nos falta|he ahorrado|"
    r"llevamos) .*(meta|metas|ahorr\w+)|"
    r"\b(mis|las|cuales son mis|revisa mis|dime mis|dame mis) "
    r"(metas|metas de ahorro)\b|"
    r"\bmetas? de ahorro\b|"
    r"\bcuanto (me )?falta para\b|"
    r"\bcuanto llevo ahorrado\b|\bcuanto he ahorrado\b|"
    r"\bcomo va mi meta\b)"
)


def _monto_estricto(texto_norm):
    """
    Como extraer_monto_flexible, pero "un/una" suelto NO cuenta como 1
    ("quiero ahorrar para un coche" no es una meta de $1).
    """

    limpio = re.sub(r"\b(un|una)\b(?!\s+(mil|millon|peso))", " ", texto_norm)

    return extraer_monto_flexible(limpio)


def _sin_plazo(texto_norm):
    """Quita 'en 6 meses' del texto y regresa (texto, (cantidad, unidad)|None)."""

    m = _RE_PLAZO.search(texto_norm)

    if not m:
        return texto_norm, None

    cant = m.group(1)
    cant = int(cant) if cant.isdigit() else _PLAZO_PALABRA[cant]

    return (texto_norm[:m.start()] + " " + texto_norm[m.end():]).strip(), (cant, m.group(2))


def _nombre_meta(resto):
    """Nombre de la meta a partir de lo que queda después del monto."""

    t = normalizar_texto(resto)

    t = re.sub(r"\b(pesos|peso|mxn|varos|lanas|mil)\b", " ", t)
    t = re.sub(r"[\d$]+", " ", t)
    t = re.sub(
        r"^(?:\s*(?:a|para|en|de|del|por|la|el|mi|mis|meta|metas|ahorro|"
        r"ahorros|que|se|llame|llamada|llamado|nombre|tipo)\b)+", " ", t
    )

    t = " ".join(t.split())

    return t[:60]


def _titulo(nombre):
    return nombre[:1].upper() + nombre[1:] if nombre else nombre


def _categoria_mencionada(texto_norm):
    for palabra, cat in _CATEGORIAS_DIRECTAS.items():
        if re.search(rf"\b{palabra}\b", texto_norm):
            return cat

    cat = detectar_categoria(texto_norm)

    return None if cat == "Otros" else cat


def _periodo_mencionado(texto_norm):
    if re.search(r"\bhoy\b", texto_norm):
        return "hoy"
    if re.search(r"\bayer\b", texto_norm):
        return "ayer"
    if re.search(r"\b(esta )?semana\b", texto_norm):
        return "semana"
    if re.search(r"\b(esta )?quincena\b", texto_norm):
        return "quincena"
    if re.search(r"\b(este )?mes\b", texto_norm):
        return "mes"
    return None


def detectar_consulta_o_meta(texto):
    """dict de intención o None."""

    t = normalizar_texto(texto)

    if not t:
        return None

    # ---------------- Consultas calculadas ----------------

    if _RE_AFECTA.search(t):
        return {"accion": "CONSULTA_AFECTA_PRESUPUESTO"}

    if _RE_GASTO_MAYOR.search(t):
        return {"accion": "CONSULTA_GASTO_MAYOR"}

    if _RE_CUANTO_LLEVO.search(t):
        return {"accion": "CONSULTA_CUANTO_LLEVO"}

    m = _RE_CUANTO_GASTE.search(t)

    if m and "presupuesto" not in t:
        resto = m.group(3)

        if re.search(r"\b(pasad[oa]s?|anterior(es)?|hace)\b", resto):
            return {"accion": "CONSULTA_GASTO_PERIODO", "periodo": "no_soportado"}

        return {
            "accion": "CONSULTA_GASTO_PERIODO",
            "periodo": _periodo_mencionado(resto),
            "categoria": _categoria_mencionada(resto),
        }

    if _RE_CONSEJO.search(t):
        return {"accion": "CONSEJO_PERSONAL", "pregunta": texto}

    # ---------------- Metas de ahorro ----------------

    if _RE_ABRIR_METAS.search(t):
        return {"accion": "ABRIR_METAS"}

    es_retiro = bool(_RE_RETIRO.search(t)) and bool(
        re.search(r"\b(meta|metas|ahorro|ahorros)\b", t)
    )
    es_abono = bool(_RE_ABONO.search(t)) or (
        bool(_RE_ABONO_AMBIGUO.search(t))
        and re.search(r"\b(meta|ahorro|ahorros|alcancia)\b", t)
    )

    if _RE_CREAR_META.search(t) or (
        re.search(r"\bahorrar\b", t) and re.search(r"\bpara\b", t)
        and _monto_estricto(t) and not es_abono
        and re.match(r"^(?:quiero|quisiera|necesito|voy a|vamos a|me gustaria|"
                     r"pretendo|planeo)\b", t)
    ):
        sin_plazo, plazo = _sin_plazo(t)
        monto = _monto_estricto(sin_plazo)

        if monto is None:
            return {"accion": "CREAR_META", "error": "sin_monto"}

        nombre = ""

        despues = re.search(r"\b(?:para|llamada|llamado|de)\s+(.+)$", sin_plazo)
        if despues:
            nombre = _nombre_meta(despues.group(1))

        # "ahorrar 10 mil para..." -> si lo capturado es solo el monto, no es nombre
        if not nombre or nombre in ("mil", "pesos"):
            nombre = "Ahorro"

        resultado = {
            "accion": "CREAR_META",
            "nombre": _titulo(nombre),
            "monto": monto,
        }

        if plazo:
            resultado["plazo"] = {"cantidad": plazo[0], "unidad": plazo[1]}

        return resultado

    if es_abono or es_retiro:
        monto = _monto_estricto(t)

        if monto is None:
            return {"accion": "ABONAR_META", "error": "sin_monto"}

        # nombre: lo que sigue al monto ("... 500 a vacaciones")
        resto = re.split(r"\d[\d,.]*(?:\s*mil)?|\bmil\b", t, maxsplit=1)
        resto = resto[1] if len(resto) > 1 else t

        nombre = _nombre_meta(resto)

        return {
            "accion": "ABONAR_META",
            "meta": nombre,
            "monto": -monto if es_retiro else monto,
        }

    if _RE_CONSULTAR_METAS.search(t):
        nombre = ""
        m2 = re.search(r"\b(?:para|con|de)\s+(?:mi |la |el )?(?:meta de )?(.+)$", t)
        if m2 and not re.match(r"^(ahorro|ahorros|metas?)$", m2.group(1)):
            nombre = _nombre_meta(m2.group(1))
        return {"accion": "CONSULTAR_METAS", "meta": nombre}

    return None
