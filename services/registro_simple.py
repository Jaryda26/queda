"""
Registro por reglas (sin IA): "gasté 150 en gasolina", "ayer compré café 45",
"cobré 3000 de un trabajo".

Es CONSERVADOR a propósito: si la frase tiene más de un número sin dejar
claro cuál es el monto, una fecha compleja ("el lunes", "el 20 de
septiembre"), dólares/euros, o dos movimientos en uno, regresa None y la
frase la maneja la IA (planes con IA) o se le explica al usuario qué
formato usar (plan Básico). Mejor no registrar que registrar mal.
"""

import re
from datetime import date, timedelta

from services.intent_engine import (
    _CENTENAS,
    _DECENAS,
    _UNIDADES,
    detectar_categoria,
    extraer_monto_flexible,
    normalizar_texto,
)

_VERBOS_GASTO = (
    "gaste", "compre", "pague", "me cobraron", "me costo", "me costaron",
    "se me fueron", "gasto",
)

_VERBOS_INGRESO = (
    "cobre", "gane", "recibi", "me depositaron", "me transfirieron",
    "me pagaron", "vendi",
)

# Fechas que las reglas no resuelven -> se la dejamos a la IA.
_FECHA_COMPLEJA = re.compile(
    r"\b(lunes|martes|miercoles|jueves|viernes|sabado|domingo|pasado|"
    r"pasada|hace|enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
    r"septiembre|setiembre|octubre|noviembre|diciembre|el \d|dia \d)\b"
)

_OTRA_MONEDA = re.compile(r"\b(dolar|dolares|usd|euro|euros|eur)\b")

_PALABRAS_NUMERO = set(_UNIDADES) | set(_DECENAS) | set(_CENTENAS)

_RELLENO = _PALABRAS_NUMERO | {
    "un", "una", "unos", "unas", "el", "la", "los", "las", "de", "del",
    "en", "por", "para", "con", "mi", "mis", "al", "a", "que", "y", "e",
    "pesos", "peso", "mxn", "varos", "lanas", "mil", "hoy", "ayer",
    "antier", "anteayer", "ya", "me", "se", "fueron", "costo", "costaron",
    "cobraron", "unos", "total", "como", "unas",
}

# Número "claro": con unidad, signo de pesos, o precedido de "por".
_MONTO_CLARO = re.compile(
    r"(?:\$\s*(\d[\d,]*(?:\.\d+)?)|(\d[\d,]*(?:\.\d+)?)\s*(?:mil\b)?\s*"
    r"(?:pesos|peso|mxn|varos|lanas)\b|\bpor (\d[\d,]*(?:\.\d+)?))"
)

_NUMEROS = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _empieza_con(texto, verbos):
    for v in verbos:
        if texto == v or texto.startswith(v + " "):
            return v
    return None


def _fecha(texto):
    """('ayer'|'antier'|'hoy'|None) -> (iso|None, texto_sin_palabra)."""

    hoy = date.today()

    for palabra, dias in (("anteayer", 2), ("antier", 2), ("ayer", 1)):
        if re.search(rf"\b{palabra}\b", texto):
            return (hoy - timedelta(days=dias)).isoformat()

    return None


def _monto(crudo, normalizado):
    """Monto sin ambigüedad o None."""

    claros = _MONTO_CLARO.findall(crudo)
    numeros_todos = _NUMEROS.findall(crudo)

    if claros and len(numeros_todos) > 1:
        # "3 tacos por 60 pesos" -> el total es el que sigue a "por"/"$".
        # "2 cocas de 25 pesos" -> ¿25 c/u o 25 en total? Mejor no adivinar.
        if not any(g3 or g1 for g1, _g2, g3 in claros):
            return None

    if claros:
        valores = {
            g.replace(",", "")
            for tupla in claros for g in tupla if g
        }
        if len(valores) != 1:
            return None
        valor = float(next(iter(valores)))
        if re.search(rf"{re.escape(next(iter(valores)))}\s*mil\b",
                     crudo.replace(",", "")):
            valor *= 1000
        return valor

    numeros = _NUMEROS.findall(crudo)

    if len(numeros) == 1:
        return extraer_monto_flexible(crudo)

    if len(numeros) > 1:
        return None

    # Sin dígitos: monto en palabras ("gasté doscientos en gasolina").
    return extraer_monto_flexible(normalizado)


def _concepto(normalizado, verbo):
    texto = normalizado

    if verbo and texto.startswith(verbo):
        texto = texto[len(verbo):]

    tokens = []

    for t in texto.split():
        if t in _RELLENO or re.fullmatch(r"[\d$]+(?:\.\d+)?", t):
            continue
        tokens.append(t)

    return " ".join(tokens[:5]).strip()


def detectar_registro_simple(texto):
    """
    Regresa un dict listo para ejecutar_accion (REGISTRAR_GASTO /
    REGISTRAR_INGRESO) más la bandera "segura" (categoría reconocida), o
    None si la frase no es un registro simple y claro.
    """

    crudo = (texto or "").lower().strip()
    normalizado = normalizar_texto(texto or "")

    if not normalizado or len(normalizado) > 140:
        return None

    # "ya" / "hoy" / "ayer" antes del verbo no cambian el sentido.
    sin_prefijo = re.sub(
        r"^(?:(?:ya|hoy|ayer|antier|anteayer|oye|mira|queda|pues)\s+)+",
        "", normalizado,
    )

    verbo_g = _empieza_con(sin_prefijo, _VERBOS_GASTO)
    verbo_i = None if verbo_g else _empieza_con(sin_prefijo, _VERBOS_INGRESO)

    verbo = verbo_g or verbo_i

    if not verbo:
        return None

    if _OTRA_MONEDA.search(normalizado) or _FECHA_COMPLEJA.search(normalizado):
        return None

    # Dos movimientos en una frase: " y gaste ", " y compre "...
    if re.search(r"\b(y|luego|despues|ademas)\s+(gaste|compre|pague|cobre|gane)\b",
                 normalizado):
        return None

    monto = _monto(crudo, normalizado)

    if monto is None or monto <= 0 or monto > 100_000_000:
        return None

    fecha = _fecha(normalizado)
    concepto = _concepto(sin_prefijo, verbo)

    if verbo_i:
        resultado = {
            "accion": "REGISTRAR_INGRESO",
            "concepto": (concepto or "Ingreso").capitalize(),
            "origen_ingreso": (concepto or "Ingreso").capitalize(),
            "monto": monto,
            "texto_original": texto,
            "segura": True,
        }
    else:
        categoria = detectar_categoria(normalizado)
        resultado = {
            "accion": "REGISTRAR_GASTO",
            "categoria": categoria,
            "concepto": (concepto or (
                categoria if categoria != "Otros" else "Gasto"
            )).capitalize(),
            "monto": monto,
            "texto_original": texto,
            "segura": categoria != "Otros",
        }

    if fecha:
        resultado["fecha"] = fecha

    return resultado
