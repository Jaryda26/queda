"""
Metas de ahorro (todos los planes, sin IA). Son de la CUENTA: en un plan
Familiar las ven y las alimentan todos los miembros.

Un abono NO se registra como gasto: es dinero que apartas, no que gastas,
así que no mueve tu presupuesto. Solo avanza la meta.
"""

from datetime import date, timedelta

from db import ejecutar_query, ejecutar_query_retornando, obtener_dataframe
from services.intent_engine import normalizar_texto

MAX_METAS_ACTIVAS = 20
MONTO_MAXIMO = 1_000_000_000


def _fecha(v):
    if v is None:
        return None
    try:
        if v != v:  # NaT / NaN
            return None
    except Exception:
        pass
    return v.date() if hasattr(v, "date") else v


def _meta(fila):
    objetivo = float(fila["monto_objetivo"])
    ahorrado = float(fila["ahorrado"] or 0)
    faltante = max(objetivo - ahorrado, 0.0)
    limite = _fecha(fila.get("fecha_limite"))
    hoy = date.today()

    dias = None
    por_semana = None

    if limite is not None and faltante > 0:
        dias = (limite - hoy).days
        if dias > 0:
            por_semana = round(faltante / max(dias / 7, 1), 2)

    return {
        "id": int(fila["id"]),
        "nombre": str(fila["nombre"]),
        "monto_objetivo": round(objetivo, 2),
        "ahorrado": round(ahorrado, 2),
        "faltante": round(faltante, 2),
        "porcentaje": round(min(ahorrado / objetivo * 100, 100), 1) if objetivo > 0 else 0.0,
        "fecha_limite": limite.isoformat() if limite else None,
        "dias_restantes": dias,
        "ahorro_semanal_sugerido": por_semana,
        "completada": bool(fila["completada"]),
    }


def listar_metas(cuenta_id):
    df = obtener_dataframe(
        """
        SELECT id, nombre, monto_objetivo, ahorrado, fecha_limite, completada
        FROM gastos.metas_ahorro
        WHERE cuenta_id = :c
        ORDER BY completada, id DESC
        """,
        {"c": cuenta_id},
    )
    return [_meta(r) for _, r in df.iterrows()]


def obtener_meta(cuenta_id, meta_id):
    df = obtener_dataframe(
        """
        SELECT id, nombre, monto_objetivo, ahorrado, fecha_limite, completada
        FROM gastos.metas_ahorro
        WHERE cuenta_id = :c AND id = :i
        """,
        {"c": cuenta_id, "i": meta_id},
    )
    return None if df.empty else _meta(df.iloc[0])


def crear_meta(usuario_id, cuenta_id, nombre, monto_objetivo, fecha_limite=None):
    """Lanza ValueError con un mensaje para el usuario si algo no es válido."""

    nombre = " ".join(str(nombre or "").split())[:80]

    if not nombre:
        raise ValueError("Ponle un nombre a tu meta.")

    try:
        monto = round(float(monto_objetivo), 2)
    except (TypeError, ValueError):
        raise ValueError("El monto de la meta no es válido.")

    if not (0 < monto <= MONTO_MAXIMO):
        raise ValueError("El monto de la meta debe ser mayor a cero.")

    if fecha_limite is not None:
        if isinstance(fecha_limite, str):
            try:
                fecha_limite = date.fromisoformat(fecha_limite)
            except ValueError:
                raise ValueError("La fecha límite no es válida.")
        if fecha_limite <= date.today():
            raise ValueError("La fecha límite debe ser futura.")

    activas = obtener_dataframe(
        "SELECT COUNT(*) AS n FROM gastos.metas_ahorro "
        "WHERE cuenta_id = :c AND completada = FALSE",
        {"c": cuenta_id},
    )
    if int(activas.iloc[0]["n"]) >= MAX_METAS_ACTIVAS:
        raise ValueError(
            f"Ya tienes {MAX_METAS_ACTIVAS} metas activas. Completa o "
            "elimina alguna antes de crear otra."
        )

    existente = buscar_meta(cuenta_id, nombre, solo_activas=True)[0]
    if existente and normalizar_texto(existente["nombre"]) == normalizar_texto(nombre):
        raise ValueError(f"Ya tienes una meta llamada {existente['nombre']}.")

    fila = ejecutar_query_retornando(
        """
        INSERT INTO gastos.metas_ahorro
            (cuenta_id, usuario_id, nombre, monto_objetivo, fecha_limite)
        VALUES (:c, :u, :n, :m, :f)
        RETURNING id
        """,
        {"c": cuenta_id, "u": usuario_id, "n": nombre, "m": monto,
         "f": fecha_limite},
    )

    return obtener_meta(cuenta_id, int(fila[0]))


def abonar(usuario_id, cuenta_id, meta_id, monto):
    """
    Suma (o resta, si es negativo) dinero a una meta. Regresa la meta
    actualizada. ValueError si el monto o la meta no son válidos.
    """

    meta = obtener_meta(cuenta_id, meta_id)

    if meta is None:
        raise ValueError("No encontré esa meta.")

    try:
        monto = round(float(monto), 2)
    except (TypeError, ValueError):
        raise ValueError("El monto no es válido.")

    if monto == 0 or abs(monto) > MONTO_MAXIMO:
        raise ValueError("El monto debe ser distinto de cero.")

    if monto > max(meta["monto_objetivo"] * 2, 1000):
        raise ValueError(
            "Ese abono es mucho mayor que la meta. Si es correcto, "
            "primero sube el monto objetivo de la meta."
        )

    if monto < 0 and meta["ahorrado"] + monto < 0:
        raise ValueError(
            f"Solo tienes {meta['ahorrado']:,.2f} ahorrados en esa meta."
        )

    nuevo = round(meta["ahorrado"] + monto, 2)
    completada = nuevo >= meta["monto_objetivo"]

    ejecutar_query(
        """
        UPDATE gastos.metas_ahorro
        SET ahorrado = :a, completada = :comp
        WHERE id = :i AND cuenta_id = :c
        """,
        {"a": nuevo, "comp": completada, "i": meta_id, "c": cuenta_id},
    )

    ejecutar_query(
        """
        INSERT INTO gastos.abonos_meta (meta_id, cuenta_id, usuario_id, monto)
        VALUES (:m, :c, :u, :monto)
        """,
        {"m": meta_id, "c": cuenta_id, "u": usuario_id, "monto": monto},
    )

    return obtener_meta(cuenta_id, meta_id)


def eliminar_meta(cuenta_id, meta_id):
    """True si existía y se borró."""

    if obtener_meta(cuenta_id, meta_id) is None:
        return False

    ejecutar_query(
        "DELETE FROM gastos.abonos_meta WHERE meta_id = :i AND cuenta_id = :c",
        {"i": meta_id, "c": cuenta_id},
    )
    ejecutar_query(
        "DELETE FROM gastos.metas_ahorro WHERE id = :i AND cuenta_id = :c",
        {"i": meta_id, "c": cuenta_id},
    )
    return True


def buscar_meta(cuenta_id, nombre, solo_activas=False):
    """
    Busca por nombre hablado ('vacaciones', 'mi laptop'). Regresa
    (meta | None, candidatas): meta si hay UNA coincidencia clara; si hay
    varias, meta=None y candidatas con todas (para preguntar cuál).
    """

    metas = listar_metas(cuenta_id)

    if solo_activas:
        metas = [m for m in metas if not m["completada"]]

    buscado = normalizar_texto(nombre or "")
    relleno = {"mi", "la", "el", "de", "para", "meta", "ahorro", "mis", "un", "una"}
    palabras = [w for w in buscado.split() if w not in relleno]

    if not palabras:
        return None, metas

    exactas = [m for m in metas if normalizar_texto(m["nombre"]) == buscado]
    if len(exactas) == 1:
        return exactas[0], exactas

    candidatas = []

    for m in metas:
        n = normalizar_texto(m["nombre"])
        if all(w in n for w in palabras) or buscado in n or n in buscado:
            candidatas.append(m)

    if len(candidatas) == 1:
        return candidatas[0], candidatas

    return None, candidatas


# ----------------------------------------------------------------------
# Textos para voz / chat
# ----------------------------------------------------------------------

def _m(x):
    return f"${float(x):,.2f}"


def describir_meta(m):
    if m["completada"]:
        return f"{m['nombre']}: ¡completada! Ahorraste {_m(m['ahorrado'])}."

    t = (
        f"{m['nombre']}: llevas {_m(m['ahorrado'])} de "
        f"{_m(m['monto_objetivo'])} ({m['porcentaje']:.0f}%), "
        f"te faltan {_m(m['faltante'])}"
    )

    if m["ahorro_semanal_sugerido"]:
        t += (
            f". Para llegar en {m['dias_restantes']} días necesitas "
            f"apartar {_m(m['ahorro_semanal_sugerido'])} por semana"
        )

    return t + "."


def resumen_metas(cuenta_id):
    metas = listar_metas(cuenta_id)

    if not metas:
        return (
            "Aún no tienes metas de ahorro. Dime, por ejemplo: quiero "
            "ahorrar 10 mil para vacaciones."
        )

    activas = [m for m in metas if not m["completada"]]
    hechas = len(metas) - len(activas)

    partes = [describir_meta(m) for m in activas[:5]]

    texto = " ".join(partes) if partes else "Todas tus metas están completas."

    if hechas and activas:
        texto += f" Además completaste {hechas}."

    return texto


def fecha_desde_plazo(cantidad, unidad):
    """('3', 'meses') -> date. unidad: dias|semanas|meses|años."""

    hoy = date.today()
    n = max(int(cantidad), 1)

    if unidad.startswith("dia"):
        return hoy + timedelta(days=n)
    if unidad.startswith("semana"):
        return hoy + timedelta(weeks=n)
    if unidad.startswith("mes"):
        return hoy + timedelta(days=30 * n)
    if unidad.startswith("ano") or unidad.startswith("año"):
        return hoy + timedelta(days=365 * n)

    return None
