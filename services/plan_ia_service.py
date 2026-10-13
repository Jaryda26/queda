"""
Qué puede hacer cada plan con y sin IA, y el límite diario de IA.

  Básico      -> sin IA. Comandos, consultas calculadas, metas de ahorro y
                 registro simple por reglas ("gasté 150 en gasolina").
  Individual  -> todo lo anterior + IA (frases libres, consejos
                 personalizados) con un tope diario de consultas.
  Familiar    -> igual que Individual, con un tope mayor (la cuenta la
                 comparten hasta 5 personas).

El tope es por CUENTA y por día (hora de México). Las consultas calculadas,
los comandos, las metas y el registro simple NUNCA gastan cupo.

Si la tabla gastos.uso_ia no existe todavía (falta correr sql/metas_ia.sql)
el contador "falla abierto": la IA sigue funcionando, solo sin tope, y se
deja un aviso en el log.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

from db import ejecutar_query, ejecutar_query_retornando, obtener_dataframe

log = logging.getLogger("queda.plan_ia")

# Consultas con IA por día, proporcional al precio del plan
# ($49 -> 30 ; $99 -> 80, porque se reparten entre hasta 5 personas).
LIMITES_IA_DIARIO = {
    "individual": 30,
    "familiar": 80,
}

LIMITE_IA_POR_DEFECTO = 30


def _hoy_mx():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Mexico_City")).date()
    except Exception:
        return datetime.now(timezone(timedelta(hours=-6))).date()


def limite_ia_diario(plan):
    """None si el plan no incluye IA; si sí, el tope de consultas por día."""

    if plan is None or not plan.get("incluye_ia", False):
        return None

    slug = str(plan.get("plan_slug") or "").lower()

    valor = os.environ.get(f"QUEDA_IA_LIMITE_{slug.upper()}")

    if valor and valor.strip().isdigit():
        return int(valor.strip())

    return LIMITES_IA_DIARIO.get(slug, LIMITE_IA_POR_DEFECTO)


def usos_ia_hoy(cuenta_id):
    try:
        df = obtener_dataframe(
            "SELECT usos FROM gastos.uso_ia "
            "WHERE cuenta_id = :c AND dia = :d",
            {"c": cuenta_id, "d": _hoy_mx()},
        )
        return 0 if df.empty else int(df.iloc[0]["usos"])
    except Exception:
        log.warning("No pude leer gastos.uso_ia (¿falta sql/metas_ia.sql?)")
        return 0


def consumir_ia(cuenta_id, plan):
    """
    Intenta gastar 1 consulta de IA. Regresa (permitido, usadas, limite).
    Es atómico: dos peticiones a la vez no pueden pasarse del tope.
    """

    limite = limite_ia_diario(plan)

    if limite is None:
        return False, 0, None

    try:
        fila = ejecutar_query_retornando(
            """
            INSERT INTO gastos.uso_ia (cuenta_id, dia, usos)
            VALUES (:c, :d, 1)
            ON CONFLICT (cuenta_id, dia)
            DO UPDATE SET usos = uso_ia.usos + 1
            WHERE uso_ia.usos < :lim
            RETURNING usos
            """,
            {"c": cuenta_id, "d": _hoy_mx(), "lim": limite},
        )
    except Exception:
        log.exception("Contador de IA no disponible; se deja pasar")
        return True, 0, limite

    if fila is None:
        return False, limite, limite

    return True, int(fila[0]), limite


def devolver_ia(cuenta_id):
    """Si la IA falló, no le cobramos la consulta al usuario."""

    try:
        ejecutar_query(
            "UPDATE gastos.uso_ia SET usos = usos - 1 "
            "WHERE cuenta_id = :c AND dia = :d AND usos > 0",
            {"c": cuenta_id, "d": _hoy_mx()},
        )
    except Exception:
        log.warning("No pude devolver la consulta de IA")


def estado_ia(cuenta_id, plan):
    """Para mostrar en la app: incluye_ia / límite / usadas / restantes."""

    limite = limite_ia_diario(plan)

    if limite is None:
        return {
            "incluye_ia": False,
            "ia_limite_diario": None,
            "ia_usadas_hoy": 0,
            "ia_restantes": None,
        }

    usadas = usos_ia_hoy(cuenta_id)

    return {
        "incluye_ia": True,
        "ia_limite_diario": limite,
        "ia_usadas_hoy": usadas,
        "ia_restantes": max(limite - usadas, 0),
    }


# ----------------------------------------------------------------------
# Mensajes
# ----------------------------------------------------------------------

AYUDA_SIN_IA = (
    "No logré entender eso con reglas simples. En tu plan puedes decir: "
    "gasté 150 en gasolina; cobré 3000; en qué he gastado más; "
    "cuánto llevo de mi presupuesto; dame un consejo; "
    "quiero ahorrar 10 mil para vacaciones; o ya pagué la luz. "
    "Con el plan Individual o Familiar también entiendo frases libres "
    "con inteligencia artificial."
)


def mensaje_limite_alcanzado(limite, plan):
    nombre = (plan or {}).get("plan_nombre") or "actual"
    return (
        f"Llegaste a tu límite de {limite} consultas con IA de hoy "
        f"(plan {nombre}); se reinicia a medianoche. Mientras tanto "
        "puedes seguir con comandos, consultas, metas y registros "
        "simples como gasté 150 en gasolina."
    )


# ----------------------------------------------------------------------
# Texto libre: reglas simples primero, IA solo si hace falta y alcanza
# ----------------------------------------------------------------------

def resolver_texto_libre(cuenta_id, texto, plan):
    """
    Se llama cuando ni las frases aprendidas ni los comandos reconocieron
    el texto. Regresa:
        ("INTENCION", dict)  -> listo para ejecutar_accion
        ("BLOQUEO", str)     -> mensaje para el usuario (sin IA, sin cupo
                                o falla de la IA)
    """

    from services.registro_simple import detectar_registro_simple

    incluye_ia = bool(plan is not None and plan.get("incluye_ia", False))

    simple = detectar_registro_simple(texto)

    # Con IA, la regla solo gana cuando está segura (categoría conocida);
    # si no, la IA entiende mejor y vale la pena su cupo.
    if simple is not None and (not incluye_ia or simple.pop("segura", False)):
        simple.pop("segura", None)
        return "INTENCION", simple

    if simple is not None:
        simple.pop("segura", None)

    if not incluye_ia:
        return "BLOQUEO", AYUDA_SIN_IA

    permitido, _, limite = consumir_ia(cuenta_id, plan)

    if not permitido:
        # Si la regla tenía una lectura razonable, mejor usarla que nada.
        if simple is not None:
            return "INTENCION", simple
        return "BLOQUEO", mensaje_limite_alcanzado(limite, plan)

    try:
        from services.interprete_ia import interpretar_movimiento
        return "INTENCION", interpretar_movimiento(texto)
    except Exception as e:
        devolver_ia(cuenta_id)
        log.exception("Falló la interpretación con IA")

        causa = type(e).__name__
        if isinstance(e, (KeyError, RuntimeError)):
            causa = "faltan credenciales AZURE_OPENAI en el servidor"

        if simple is not None:
            return "INTENCION", simple

        return "BLOQUEO", f"No pude interpretar eso ahora mismo (IA: {causa})."
