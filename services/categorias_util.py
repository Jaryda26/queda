"""
Categorías: una sola forma de escribirlas ("COMIDA" y "Comida" eran dos
categorías distintas) y categoría correcta para los pagos de recordatorios
(antes todos caían en "Recordatorio", que no dice nada).
"""

import re

from services.intent_engine import normalizar_texto

CATEGORIAS = [
    "Gasolina", "Comida", "Servicios", "Transporte", "Salud",
    "Entretenimiento", "Deudas", "Otros",
]

_POR_CLAVE = {normalizar_texto(c): c for c in CATEGORIAS}

# Sinónimos que ya existen en la base o que la IA suele devolver.
_SINONIMOS = {
    "deuda": "Deudas", "bancos": "Deudas", "banco": "Deudas",
    "tarjeta": "Deudas", "tarjetas": "Deudas", "credito": "Deudas",
    "creditos": "Deudas", "prestamo": "Deudas", "prestamos": "Deudas",
    "alimentos": "Comida", "alimentacion": "Comida",
    "restaurante": "Comida", "restaurantes": "Comida", "super": "Comida",
    "supermercado": "Comida", "servicio": "Servicios",
    "entretenimiento": "Entretenimiento", "ocio": "Entretenimiento",
    "medico": "Salud", "transportes": "Transporte",
    "combustible": "Gasolina", "sin categoria": "Otros", "": "Otros",
}


def canonizar_categoria(categoria):
    """'COMIDA ' -> 'Comida'; desconocida -> Primera Mayúscula."""

    texto = " ".join(str(categoria or "").split())
    clave = normalizar_texto(texto)

    if clave in _POR_CLAVE:
        return _POR_CLAVE[clave]

    if clave in _SINONIMOS:
        return _SINONIMOS[clave]

    return texto[:1].upper() + texto[1:].lower() if texto else "Otros"


_DEUDAS = re.compile(
    r"\b(tarjeta|banco|bbva|bancomer|banorte|santander|hsbc|banamex|"
    r"citibanamex|citi|scotiabank|inbursa|bajio|afirme|banregio|azteca|"
    r"credito|prestamo|hipoteca|financiamiento|credileasing|sears|coppel|"
    r"liverpool|palacio de hierro|mercado pago|nu bank|nubank|klar|"
    r"amex|american express|visa|mastercard|deuda|adeudo|mensualidad "
    r"del (auto|carro|coche)|abono|pagare)\b"
)


def categoria_de_pago(descripcion):
    """
    Categoría para el gasto que genera pagar un recordatorio, según lo
    que dice su descripción: "Tarjeta BBVA" -> Deudas, "Luz CFE" ->
    Servicios, "Netflix" -> Entretenimiento. Si no hay pista: Otros.
    """

    from services.intent_engine import detectar_categoria

    t = normalizar_texto(descripcion or "")

    if _DEUDAS.search(t):
        return "Deudas"

    return detectar_categoria(t)
