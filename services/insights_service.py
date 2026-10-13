"""
Consultas personalizadas CALCULADAS (sin IA): en qué gastas más, qué afecta
tu presupuesto, cuánto llevas, cuánto puedes gastar al día y consejos
basados en tus propios números. Funcionan en todos los planes.

Para los planes con IA, contexto_financiero() entrega esos mismos números
ya calculados para que la IA solo los redacte (nunca los inventa).
"""

from datetime import date, datetime, timedelta

from db import obtener_dataframe
from services.categorias_util import canonizar_categoria
from services.presupuesto_service import (
    obtener_estado_presupuesto,
    periodo_anterior,
    periodo_para,
)

_MESES = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
]


def _m(x):
    return f"${float(x):,.2f}"


def _corta(d):
    return f"{d.day} {_MESES[d.month - 1]}"


def _dt(d):
    return datetime.combine(d, datetime.min.time())


def _gastos(cuenta_id, inicio, fin):
    """Gastos entre dos fechas (ambas incluidas)."""

    df = obtener_dataframe(
        """
        SELECT concepto, COALESCE(categoria, 'Otros') AS categoria,
               monto, fecha
        FROM gastos.movimientos
        WHERE tipo = 'GASTO' AND cuenta_id = :c
          AND fecha >= :ini AND fecha < :fin
        """,
        {"c": cuenta_id, "ini": _dt(inicio), "fin": _dt(fin + timedelta(days=1))},
    )

    # "COMIDA" y "Comida" son la misma categoría.
    if not df.empty:
        df["categoria"] = df["categoria"].map(canonizar_categoria)

    return df


def _total(cuenta_id, tipo, inicio, fin):
    df = obtener_dataframe(
        """
        SELECT COALESCE(SUM(monto), 0) AS t
        FROM gastos.movimientos
        WHERE tipo = :t AND cuenta_id = :c
          AND fecha >= :ini AND fecha < :fin
        """,
        {"t": tipo, "c": cuenta_id,
         "ini": _dt(inicio), "fin": _dt(fin + timedelta(days=1))},
    )
    return float(df.iloc[0]["t"]) if not df.empty else 0.0


def _contar(cuenta_id, inicio, fin):
    df = obtener_dataframe(
        """
        SELECT COUNT(*) AS n FROM gastos.movimientos
        WHERE cuenta_id = :c AND fecha >= :ini AND fecha < :fin
        """,
        {"c": cuenta_id, "ini": _dt(inicio),
         "fin": _dt(fin + timedelta(days=1))},
    )
    return int(df.iloc[0]["n"]) if not df.empty else 0


def _por_categoria(df):
    if df.empty:
        return []
    g = df.groupby("categoria")["monto"].agg(["sum", "count"])
    g = g.sort_values("sum", ascending=False)
    return [(str(c), float(r["sum"]), int(r["count"])) for c, r in g.iterrows()]


TIPOS_VISTA = ("SEMANAL", "QUINCENAL", "MENSUAL")


def periodo_analisis(cuenta_id, offset=0, tipo=None):
    """
    El periodo del presupuesto (semana desde tu día de inicio, quincena
    1-15/16-fin o mes natural); sin presupuesto, el mes natural en curso.
    offset: 0 = actual, -1 = el anterior, -2 = hace dos...
    tipo: SEMANAL | QUINCENAL | MENSUAL para ver otra escala (en ese caso
    el presupuesto no se compara, porque es de otro tipo de periodo).
    Incluye el periodo anterior equivalente para comparar.
    """

    hoy = date.today()
    est0 = obtener_estado_presupuesto(cuenta_id)
    offset = min(int(offset or 0), 0)

    dia = est0["dia_inicio"] if est0 else 0
    tipo_sel = str(tipo or (est0["tipo_periodo"] if est0 else "MENSUAL")).upper()

    if tipo_sel not in TIPOS_VISTA:
        tipo_sel = "MENSUAL"

    inicio, fin = periodo_para(tipo_sel, dia, hoy)

    for _ in range(-offset):
        inicio, fin = periodo_anterior(tipo_sel, dia, inicio)

    p_ini, p_fin = periodo_anterior(tipo_sel, dia, inicio)

    est = None

    if est0 and tipo_sel == est0["tipo_periodo"]:
        if offset == 0:
            est = est0
        else:
            gastado = _total(cuenta_id, "GASTO", inicio, fin)
            monto = est0["monto"]
            est = dict(
                est0,
                fecha_inicio=inicio.isoformat(),
                fecha_fin=fin.isoformat(),
                gastado=round(gastado, 2),
                restante=round(monto - gastado, 2),
                porcentaje=round(gastado / monto * 100, 1) if monto > 0 else 0.0,
                dias_restantes=0,
            )

    rango = f"({_corta(inicio)} al {_corta(fin)})"

    if offset < 0:
        etiqueta = f"el periodo del {_corta(inicio)} al {_corta(fin)}"
    elif est:
        etiqueta = f"tu periodo {rango}"
    else:
        etiqueta = {
            "SEMANAL": "esta semana",
            "QUINCENAL": "esta quincena",
        }.get(tipo_sel, "este mes") + f" {rango}"

    dias_totales = (fin - inicio).days + 1
    transcurridos = max((min(hoy, fin) - inicio).days + 1, 1)

    return {
        "inicio": inicio,
        "fin": fin,
        "hoy": hoy,
        "offset": offset,
        "tipo": tipo_sel,
        "presupuesto": est,
        "dias_totales": dias_totales,
        "dias_transcurridos": transcurridos,
        "dias_restantes": max((fin - hoy).days + 1, 0),
        "prev_inicio": p_ini,
        "prev_fin": p_fin,
        "etiqueta": etiqueta,
    }


def _pagos_pendientes(cuenta_id, hasta):
    """Pagos (recordatorios tipo PAGO) sin pagar que vencen antes de 'hasta'."""

    try:
        df = obtener_dataframe(
            """
            SELECT descripcion, monto, fecha_vencimiento
            FROM gastos.recordatorios
            WHERE cuenta_id = :c AND pagado = FALSE AND tipo = 'PAGO'
            ORDER BY fecha_vencimiento
            """,
            {"c": cuenta_id},
        )
    except Exception:
        return 0.0, 0

    total = 0.0
    n = 0

    for _, r in df.iterrows():
        v = r["fecha_vencimiento"]
        v = v.date() if hasattr(v, "date") else v
        if v <= hasta:
            total += float(r["monto"] or 0)
            n += 1

    return total, n


# ----------------------------------------------------------------------
# Datos base reutilizados por todas las respuestas
# ----------------------------------------------------------------------

def analizar(cuenta_id, offset=0, tipo=None):
    p = periodo_analisis(cuenta_id, offset, tipo)

    actual = _gastos(cuenta_id, p["inicio"], p["fin"])
    previo = _gastos(cuenta_id, p["prev_inicio"], p["prev_fin"])

    total = float(actual["monto"].sum()) if not actual.empty else 0.0
    total_previo = float(previo["monto"].sum()) if not previo.empty else 0.0

    cats = _por_categoria(actual)
    cats_prev = {c: t for c, t, _ in _por_categoria(previo)}

    mayor = None
    if not actual.empty:
        fila = actual.sort_values("monto", ascending=False).iloc[0]
        f = fila["fecha"]
        f = f.date() if hasattr(f, "date") else f
        mayor = {
            "concepto": str(fila["concepto"] or "Gasto"),
            "categoria": str(fila["categoria"]),
            "monto": float(fila["monto"]),
            "fecha": f,
        }

    ingresos = _total(cuenta_id, "INGRESO", p["inicio"], p["fin"])
    ritmo = total / p["dias_transcurridos"]
    # Solo se proyecta con suficientes días de datos (con 1 día, un gasto
    # grande haría una proyección absurda) y si aún no se pasó.
    proyeccion_gasto = None
    est = p["presupuesto"]
    if (
        est
        and p["offset"] == 0
        and est["restante"] > 0
        and p["dias_transcurridos"] >= max(3, 0.3 * p["dias_totales"])
    ):
        proyeccion_gasto = ritmo * p["dias_totales"]

    # Categorías que subieron claramente contra el periodo anterior.
    subieron = []
    for c, t, _ in cats:
        antes = cats_prev.get(c, 0.0)
        if antes >= 100 and t - antes >= 100 and (t - antes) / antes >= 0.30:
            subieron.append((c, t, antes))

    return {
        "p": p, "total": total, "total_previo": total_previo,
        "ingresos": ingresos, "resultado": ingresos - total,
        "cats": cats, "cats_prev": cats_prev, "mayor": mayor,
        "ritmo": ritmo, "proyeccion_gasto": proyeccion_gasto,
        "subieron": subieron,
    }


# ----------------------------------------------------------------------
# Respuestas
# ----------------------------------------------------------------------

def _resultado_txt(a):
    """'a favor' / 'en contra' del periodo (ingresos - gastos)."""

    r = a["resultado"]

    if r >= 0:
        return f"a favor por {_m(r)}"

    return f"en contra por {_m(-r)}"


def _nota_deudas(cat):
    return " (tus pagos a bancos y deudas)" if cat == "Deudas" else ""


def en_que_gasto_mas(cuenta_id):
    a = analizar(cuenta_id)
    p = a["p"]

    if a["total"] <= 0:
        return (
            f"Aún no tienes gastos registrados en {p['etiqueta']}. "
            "Dime por ejemplo: gasté 150 en gasolina."
        )

    texto = f"En {p['etiqueta']} gastaste {_m(a['total'])}"

    if a["ingresos"] > 0:
        texto += f" y recibiste {_m(a['ingresos'])}"

    texto += ". "

    c0, t0, _ = a["cats"][0]

    texto += (
        f"Tu mayor egreso es {c0}{_nota_deudas(c0)} con {_m(t0)} "
        f"({t0 / a['total'] * 100:.0f}%)"
    )

    otros = [
        f"{c} {_m(t)} ({t / a['total'] * 100:.0f}%)"
        for c, t, _ in a["cats"][1:3]
    ]

    if otros:
        texto += (
            "; le sigue " if len(otros) == 1 else "; le siguen "
        ) + " y ".join(otros)

    texto += "."

    m = a["mayor"]
    if m:
        texto += (
            f" Tu gasto individual más grande fue {_m(m['monto'])} en "
            f"{m['concepto']} el {_corta(m['fecha'])}."
        )

    return texto


def _linea_presupuesto(a, con_resultado=True):
    """Cómo va el presupuesto SIN confundirlo con el saldo del periodo."""

    est = a["p"]["presupuesto"]

    if est["restante"] < 0:
        t = f"Te pasaste {_m(-est['restante'])} del presupuesto de gasto ({est['porcentaje']:.0f}% usado)."

        if not con_resultado:
            pass
        elif a["ingresos"] > 0 and a["resultado"] >= 0:
            t += (
                f" Aun así tu periodo va a favor por {_m(a['resultado'])} "
                f"porque ingresaste {_m(a['ingresos'])}: el presupuesto es "
                "un tope de gasto, no tu saldo."
            )
        elif a["ingresos"] > 0:
            t += (
                f" Además gastaste más de lo que ingresaste "
                f"({_resultado_txt(a)})."
            )

        return t

    return (
        f"Llevas {est['porcentaje']:.0f}% de tu presupuesto: gastaste "
        f"{_m(est['gastado'])} de {_m(est['monto'])} y te quedan "
        f"{_m(est['restante'])}."
    )


def que_afecta_presupuesto(cuenta_id):
    a = analizar(cuenta_id)
    p = a["p"]
    est = p["presupuesto"]

    if a["total"] <= 0:
        return (
            f"No tienes gastos registrados en {p['etiqueta']}, así que "
            "nada está afectando tu presupuesto por ahora."
        )

    top, top_t, _ = a["cats"][0]

    if not est or est["monto"] <= 0:
        return (
            f"Aún no tienes un presupuesto definido. En {p['etiqueta']} "
            f"lo que más pesa es {top}{_nota_deudas(top)} con {_m(top_t)} "
            f"({top_t / a['total'] * 100:.0f}% de tus gastos). "
            "Dime: pon mi presupuesto semanal en 2000 pesos, y te digo "
            "qué lo afecta."
        )

    texto = _linea_presupuesto(a)

    texto += (
        f" Lo que más lo afecta es {top}{_nota_deudas(top)} con "
        f"{_m(top_t)} ({top_t / a['total'] * 100:.0f}% de tus gastos)."
    )

    if len(a["cats"]) > 1:
        c2, t2, _ = a["cats"][1]
        texto += f" Le sigue {c2} con {_m(t2)}."

    if a["subieron"]:
        c, t, antes = max(a["subieron"], key=lambda x: x[1] - x[2])
        texto += (
            f" {c} subió {(t - antes) / antes * 100:.0f}% contra el "
            f"periodo anterior (+{_m(t - antes)})."
        )

    m = a["mayor"]
    if m and m["monto"] >= a["total"] * 0.25 and len(a["cats"]) > 1:
        texto += (
            f" Un solo gasto de {_m(m['monto'])} en {m['concepto']} "
            "pesa bastante."
        )

    pend, n = _pagos_pendientes(cuenta_id, p["fin"])
    if n:
        texto += (
            f" Además tienes {n} pago{'s' if n != 1 else ''} pendiente"
            f"{'s' if n != 1 else ''} por {_m(pend)} que "
            f"vence{'n' if n != 1 else ''} antes de que cierre el periodo."
        )

    if a["proyeccion_gasto"] is not None and a["proyeccion_gasto"] > est["monto"]:
        exceso = a["proyeccion_gasto"] - est["monto"]
        texto += (
            f" A este ritmo terminarías el periodo pasándote unos "
            f"{_m(exceso)}."
        )

    return texto


def cuanto_llevo(cuenta_id):
    a = analizar(cuenta_id)
    p = a["p"]
    est = p["presupuesto"]

    if not est or est["monto"] <= 0:
        return (
            "Aún no tienes un presupuesto definido. Dime: pon mi "
            "presupuesto semanal en 2000 pesos."
        )

    dias = max(est["dias_restantes"], 1)

    if est["restante"] <= 0:
        t = _linea_presupuesto(a)
        return t + f" Te quedan {est['dias_restantes']} días de periodo."

    diario = est["restante"] / dias

    return (
        f"Llevas {_m(est['gastado'])} de {_m(est['monto'])} "
        f"({est['porcentaje']:.0f}%). Te quedan {_m(est['restante'])} "
        f"para {est['dias_restantes']} "
        f"día{'s' if est['dias_restantes'] != 1 else ''}; "
        f"puedes gastar unos {_m(diario)} al día."
    )


def resumen_periodo(cuenta_id, offset=0, tipo=None):
    """La historia completa del periodo: ingresos, gastos, resultado,
    presupuesto, mayor egreso y una recomendación."""

    a = analizar(cuenta_id, offset, tipo)
    p = a["p"]
    est = p["presupuesto"]

    if a["total"] <= 0 and a["ingresos"] <= 0:
        return (
            f"En {p['etiqueta']} aún no hay movimientos. Registra tus "
            "gastos e ingresos con la voz y te cuento cómo vas."
        )

    texto = (
        f"En {p['etiqueta']} ingresaste {_m(a['ingresos'])} y gastaste "
        f"{_m(a['total'])}: tu periodo va {_resultado_txt(a)}."
    )

    if est and est["monto"] > 0:
        texto += " " + _linea_presupuesto(a, con_resultado=False)

    if a["cats"]:
        c0, t0, _ = a["cats"][0]
        texto += (
            f" Tu mayor egreso es {c0}{_nota_deudas(c0)} con {_m(t0)} "
            f"({t0 / a['total'] * 100:.0f}%)."
        )

    pend, n = (
        _pagos_pendientes(cuenta_id, p["fin"])
        if p["offset"] == 0 else (0.0, 0)
    )

    if n:
        cierre = a["resultado"] - pend
        texto += (
            f" Te faltan {n} pago{'s' if n != 1 else ''} por {_m(pend)} "
            f"antes de que cierre el periodo; si los pagas, cerrarías "
            + (f"a favor por {_m(cierre)}." if cierre >= 0
               else f"en contra por {_m(-cierre)}.")
        )

    tips = (
        consejos_calculados(cuenta_id, maximo=1)
        if p["offset"] == 0 and (p["presupuesto"] or not tipo) else []
    )
    if tips:
        texto += " Recomendación: " + tips[0]

    return texto


def kpis_periodo(cuenta_id, offset=0, tipo=None):
    """Cifras del periodo para los dashboards (web y celular)."""

    a = analizar(cuenta_id, offset, tipo)
    p = a["p"]
    est = p["presupuesto"]

    saldo = _total(cuenta_id, "INGRESO", date(2000, 1, 1), date.today()) - _total(
        cuenta_id, "GASTO", date(2000, 1, 1), date.today()
    )

    monto = est["monto"] if est else 0.0

    return {
        "etiqueta": p["etiqueta"],
        "inicio": p["inicio"],
        "fin": p["fin"],
        "tiene_presupuesto": bool(est),
        "ingresos": a["ingresos"],
        "gastos": a["total"],
        "resultado": a["resultado"],
        "presupuesto": monto,
        "porcentaje": round(a["total"] / monto * 100, 1) if monto > 0 else 0.0,
        "restante": (monto - a["total"]) if monto > 0 else None,
        "dias_restantes": p["dias_restantes"] if p["offset"] == 0 else None,
        "es_actual": p["offset"] == 0,
        "tipo": p["tipo"],
        "saldo_acumulado": saldo,
        "movimientos": _contar(cuenta_id, p["inicio"], p["fin"]),
        "categorias": [(c, t) for c, t, _ in a["cats"]],
    }


_DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

VENTANA_DIAS_SEMANA = 56  # 8 semanas


def _gasto_por_dia_semana(cuenta_id):
    """
    [(dia, total, promedio_por_ese_dia, categoria_principal)] ordenado de
    mayor a menor total, sobre las últimas 8 semanas. None si hay pocos
    datos (menos de 14 días desde el primer gasto).
    """

    hoy = date.today()
    df = _gastos(cuenta_id, hoy - timedelta(days=VENTANA_DIAS_SEMANA - 1), hoy)

    if df.empty:
        return None

    primero = df["fecha"].min()
    primero = primero.date() if hasattr(primero, "date") else primero

    if (hoy - primero).days < 13:
        return None

    ventana = (hoy - primero).days + 1

    df = df.copy()
    df["dia"] = df["fecha"].map(lambda f: f.weekday())

    resultado = []

    for dia in range(7):
        sub = df[df["dia"] == dia]
        if sub.empty:
            continue
        # cuántas veces cayó ese día de la semana dentro de la ventana
        veces = sum(
            1 for i in range(ventana)
            if (primero + timedelta(days=i)).weekday() == dia
        )
        cats = _por_categoria(sub)
        resultado.append((
            dia, float(sub["monto"].sum()),
            float(sub["monto"].sum()) / max(veces, 1),
            cats[0][0] if cats else "Otros",
        ))

    resultado.sort(key=lambda x: x[1], reverse=True)

    return resultado


def dia_semana_mayor_gasto(cuenta_id):
    datos = _gasto_por_dia_semana(cuenta_id)

    if not datos:
        return (
            "Aún tengo pocos datos para saber qué día de la semana gastas "
            "más: necesito al menos dos semanas de movimientos."
        )

    d, total, prom, cat = datos[0]

    texto = (
        f"El día que más gastas es el {_DIAS_ES[d]}: en las últimas "
        f"semanas llevas {_m(total)} en ese día, unos {_m(prom)} cada "
        f"{_DIAS_ES[d]}, sobre todo en {cat}."
    )

    if len(datos) > 1:
        d2, t2, p2, _ = datos[1]
        texto += f" Le sigue el {_DIAS_ES[d2]} con {_m(t2)}."

    barato = datos[-1]
    if len(datos) > 3:
        texto += f" Tu día más tranquilo es el {_DIAS_ES[barato[0]]}."

    return texto


def categoria_vs_ingreso(cuenta_id):
    """Qué parte de tu ingreso se va a cada categoría."""

    a = analizar(cuenta_id)
    p = a["p"]

    ingreso = a["ingresos"]
    etiqueta = p["etiqueta"]

    if ingreso <= 0:
        hoy = date.today()
        ingreso = _total(cuenta_id, "INGRESO", hoy - timedelta(days=29), hoy)
        etiqueta = "los últimos 30 días"
        if ingreso <= 0:
            return (
                "Aún no tienes ingresos registrados, así que no puedo "
                "calcular qué parte se va a cada categoría. Dime por "
                "ejemplo: me depositaron 12000 pesos."
            )
        hoy = date.today()
        df = _gastos(cuenta_id, hoy - timedelta(days=29), hoy)
        cats = _por_categoria(df)
        total = float(df["monto"].sum()) if not df.empty else 0.0
    else:
        cats = a["cats"]
        total = a["total"]

    if not cats:
        return f"En {etiqueta} no tienes gastos: todo tu ingreso sigue contigo."

    partes = [
        f"{c} {t / ingreso * 100:.0f}% ({_m(t)})" for c, t, _ in cats[:3]
    ]

    c0, t0, _ = cats[0]

    texto = (
        f"De tu ingreso de {_m(ingreso)} en {etiqueta}, la categoría que "
        f"más lo diluye es {c0}{_nota_deudas(c0)}: se lleva "
        f"{t0 / ingreso * 100:.0f}%. Reparto: " + "; ".join(partes) + "."
    )

    resto = ingreso - total

    texto += (
        f" Te quedan {_m(resto)} ({resto / ingreso * 100:.0f}% del ingreso)."
        if resto >= 0 else
        f" Gastaste {_m(-resto)} más de lo que ingresó."
    )

    return texto



def _rango_periodo(clave):
    hoy = date.today()

    if clave == "hoy":
        return hoy, hoy, "hoy"
    if clave == "ayer":
        ayer = hoy - timedelta(days=1)
        return ayer, ayer, "ayer"
    if clave == "semana":
        return hoy - timedelta(days=hoy.weekday()), hoy, "esta semana"
    if clave == "quincena":
        ini = hoy.replace(day=1 if hoy.day <= 15 else 16)
        return ini, hoy, "esta quincena"
    if clave == "mes":
        return hoy.replace(day=1), hoy, "este mes"
    return None


def cuanto_gaste(cuenta_id, periodo=None, categoria=None):
    """periodo: hoy|ayer|semana|quincena|mes|None (=periodo del presupuesto)."""

    if periodo == "no_soportado":
        return (
            "Por ahora calculo hoy, ayer, esta semana, esta quincena, "
            "este mes o el periodo de tu presupuesto."
        )

    rango = _rango_periodo(periodo) if periodo else None

    if rango:
        inicio, fin, etiqueta = rango
    else:
        p = periodo_analisis(cuenta_id)
        inicio, fin, etiqueta = p["inicio"], min(p["fin"], date.today()), p["etiqueta"]
        etiqueta = "en " + etiqueta

    df = _gastos(cuenta_id, inicio, fin)

    if categoria:
        df = df[df["categoria"] == categoria]

    sujeto = f"en {categoria}" if categoria else "en total"

    if df.empty:
        return f"No tienes gastos {sujeto} {etiqueta}."

    total = float(df["monto"].sum())
    n = len(df)

    return (
        f"Gastaste {_m(total)} {sujeto} {etiqueta}, "
        f"en {n} movimiento{'s' if n != 1 else ''}."
    )


# ----------------------------------------------------------------------
# Consejos calculados (sin IA)
# ----------------------------------------------------------------------

def consejos_calculados(cuenta_id, maximo=3):
    a = analizar(cuenta_id)
    p = a["p"]
    est = p["presupuesto"]
    tips = []  # (prioridad, texto) — menor número = más importante

    if a["total"] <= 0 and not est:
        return [
            "Empieza registrando tus gastos con la voz, por ejemplo: "
            "gasté 150 en gasolina. Con unos días de datos te doy "
            "consejos basados en tus números."
        ]

    if not est or est["monto"] <= 0:
        tips.append((1, (
            "Define un presupuesto: es lo que más ayuda a controlar el "
            "gasto. Dime, por ejemplo: pon mi presupuesto semanal en "
            "2000 pesos."
        )))
    else:
        top = a["cats"][0][0] if a["cats"] else None

        if est["restante"] < 0 and a["ingresos"] > 0 and a["resultado"] >= 0:
            tips.append((1, (
                f"Te pasaste {_m(-est['restante'])} de tu presupuesto de "
                f"gasto, aunque el periodo va a favor por "
                f"{_m(a['resultado'])}. Vigila "
                + (f"{top}" if top else "tus gastos")
                + " para que el próximo periodo no te alcance el tope."
            )))
        elif est["restante"] < 0:
            tips.append((0, (
                f"Ya te pasaste {_m(-est['restante'])} del presupuesto. "
                "Lo mejor es pausar gastos no esenciales"
                + (f", empezando por {top}" if top else "") + "."
            )))
        elif est["porcentaje"] >= 80:
            dias = max(est["dias_restantes"], 1)
            tips.append((0, (
                f"Ya usaste {est['porcentaje']:.0f}% del presupuesto. "
                f"Te quedan {_m(est['restante'])} para "
                f"{est['dias_restantes']} días: procura no pasar de "
                f"{_m(est['restante'] / dias)} al día."
            )))
        elif a["proyeccion_gasto"] and a["proyeccion_gasto"] > est["monto"]:
            exceso = a["proyeccion_gasto"] - est["monto"]
            tips.append((1, (
                f"Al ritmo actual terminarías el periodo pasándote "
                f"unos {_m(exceso)}. Baja tu gasto diario de "
                f"{_m(a['ritmo'])} un poco para llegar justo."
            )))
        elif (
            est["porcentaje"] <= 60
            and p["dias_transcurridos"] >= p["dias_totales"] * 0.6
            and _pagos_pendientes(cuenta_id, p["fin"])[1] == 0
        ):
            tips.append((4, (
                f"Vas muy bien: usaste {est['porcentaje']:.0f}% de tu "
                "presupuesto y ya casi termina el periodo. Lo que sobre "
                "puedes mandarlo a una meta de ahorro."
            )))

    if a["cats"] and a["total"] > 0:
        c, t, _ = a["cats"][0]
        share = t / a["total"] * 100
        if c == "Deudas" and share >= 35:
            tips.append((1, (
                f"Tu mayor egreso son tus pagos a bancos y deudas "
                f"({_m(t)}, {share:.0f}% de tus gastos). Atiende tus "
                "obligaciones bancarias a tiempo para evitar intereses "
                "y, si puedes, adelanta pagos a la deuda más cara."
            )))
        elif share >= 40 and len(a["cats"]) > 1:
            tips.append((2, (
                f"{c} concentra {share:.0f}% de tus gastos "
                f"({_m(t)}). Ponerte un tope en esa categoría es lo que "
                "más impacto tendría."
            )))

    if a["subieron"]:
        c, t, antes = max(a["subieron"], key=lambda x: x[1] - x[2])
        tips.append((2, (
            f"Tu gasto en {c} subió {(t - antes) / antes * 100:.0f}% "
            f"contra el periodo anterior (+{_m(t - antes)}). Revisa si "
            "fue algo puntual o ya es costumbre."
        )))

    if est:
        pend, n = _pagos_pendientes(cuenta_id, p["fin"])
        if n and est["restante"] - pend < 0:
            tips.append((1, (
                f"Ojo: tienes {n} pago{'s' if n != 1 else ''} por "
                f"{_m(pend)} antes de que cierre el periodo y solo te "
                f"quedan {_m(est['restante'])}. Aparta ese dinero ya."
            )))

    # Ahorro: ingresos vs gastos de los últimos 30 días
    hoy = date.today()
    ini30 = hoy - timedelta(days=29)
    ing = _total(cuenta_id, "INGRESO", ini30, hoy)
    gas = _total(cuenta_id, "GASTO", ini30, hoy)

    try:
        from services.metas_service import listar_metas
        metas = [m for m in listar_metas(cuenta_id) if not m["completada"]]
    except Exception:
        metas = []

    if ing > 0:
        libre = ing - gas
        if libre < 0:
            tips.append((1, (
                f"En los últimos 30 días gastaste {_m(-libre)} más de "
                "lo que ingresó. Conviene recortar antes de pensar en ahorrar."
            )))
        elif libre > 0:
            sugerido = round(libre * 0.2, 2)
            if metas:
                m = metas[0]
                tips.append((3, (
                    f"En los últimos 30 días te sobraron {_m(libre)}. Si apartas "
                    f"{_m(sugerido)} (20%) a tu meta {m['nombre']}, la "
                    "alcanzas más rápido. Di: abona a mi meta."
                )))
            else:
                tips.append((3, (
                    f"En los últimos 30 días te sobraron {_m(libre)}. Apartar 20% "
                    f"({_m(sugerido)}) es un buen inicio: crea una meta "
                    "diciendo, por ejemplo, quiero ahorrar 10 mil para "
                    "vacaciones."
                )))

    if not tips:
        tips.append((5, (
            "Tus números se ven estables. Mantén el hábito de registrar "
            "cada gasto y revisa tu presupuesto una vez por semana."
        )))

    tips.sort(key=lambda x: x[0])

    return [t for _, t in tips[:maximo]]


def consejo_texto(cuenta_id):
    tips = consejos_calculados(cuenta_id)
    return "Esto es lo que veo en tus números. " + " ".join(
        f"{i}. {t}" for i, t in enumerate(tips, 1)
    )


# ----------------------------------------------------------------------
# Contexto para la IA (planes Individual / Familiar)
# ----------------------------------------------------------------------

def contexto_financiero(cuenta_id):
    a = analizar(cuenta_id)
    p = a["p"]
    est = p["presupuesto"]

    hoy = date.today()
    ini30 = hoy - timedelta(days=29)

    ctx = {
        "periodo": {
            "desde": p["inicio"].isoformat(),
            "hasta": p["fin"].isoformat(),
            "es_periodo_de_presupuesto": bool(est),
            "dias_transcurridos": p["dias_transcurridos"],
            "dias_restantes": p["dias_restantes"],
        },
        "gasto_total_periodo": round(a["total"], 2),
        "gasto_total_periodo_anterior": round(a["total_previo"], 2),
        "gasto_diario_promedio": round(a["ritmo"], 2),
        "categorias_que_mas_pesan": [
            {"categoria": c, "total": round(t, 2),
             "porcentaje": round(t / a["total"] * 100, 1) if a["total"] else 0,
             "periodo_anterior": round(a["cats_prev"].get(c, 0.0), 2)}
            for c, t, _ in a["cats"][:5]
        ],
        "ingresos_ultimos_30_dias": round(_total(cuenta_id, "INGRESO", ini30, hoy), 2),
        "gastos_ultimos_30_dias": round(_total(cuenta_id, "GASTO", ini30, hoy), 2),
    }

    if a["mayor"]:
        m = a["mayor"]
        ctx["gasto_individual_mas_grande"] = {
            "concepto": m["concepto"], "monto": round(m["monto"], 2),
            "categoria": m["categoria"], "fecha": m["fecha"].isoformat(),
        }

    if est:
        ctx["presupuesto"] = {
            "tipo": est["tipo_periodo"], "monto": est["monto"],
            "gastado": est["gastado"], "restante": est["restante"],
            "porcentaje_usado": est["porcentaje"],
        }
        if a["proyeccion_gasto"] is not None:
            ctx["presupuesto"]["gasto_proyectado_fin_periodo"] = round(
                a["proyeccion_gasto"], 2
            )
        pend, n = _pagos_pendientes(cuenta_id, p["fin"])
        ctx["pagos_pendientes_en_el_periodo"] = {"cantidad": n, "total": round(pend, 2)}

    try:
        from services.metas_service import listar_metas
        ctx["metas_de_ahorro"] = [
            {"nombre": m["nombre"], "objetivo": m["monto_objetivo"],
             "ahorrado": m["ahorrado"], "faltante": m["faltante"],
             "porcentaje": m["porcentaje"],
             "dias_restantes": m["dias_restantes"],
             "ahorro_semanal_sugerido": m["ahorro_semanal_sugerido"]}
            for m in listar_metas(cuenta_id) if not m["completada"]
        ][:5]
    except Exception:
        pass

    ctx["ingresos_del_periodo"] = round(a["ingresos"], 2)
    ctx["resultado_del_periodo_ingresos_menos_gastos"] = round(a["resultado"], 2)

    if a["ingresos"] > 0:
        for item in ctx["categorias_que_mas_pesan"]:
            item["porcentaje_del_ingreso"] = round(
                item["total"] / a["ingresos"] * 100, 1
            )

    try:
        dias = _gasto_por_dia_semana(cuenta_id)
        if dias:
            ctx["gasto_por_dia_de_semana_ultimas_8_semanas"] = [
                {"dia": _DIAS_ES[d], "total": round(t, 2),
                 "promedio": round(pr, 2), "categoria_principal": c}
                for d, t, pr, c in dias
            ]
    except Exception:
        pass

    try:
        mes = periodo_para("MENSUAL", 0, hoy)[0]
        meses = []
        for _ in range(3):
            ini, fin_m = periodo_para("MENSUAL", 0, mes)
            meses.append({
                "mes": ini.strftime("%Y-%m"),
                "ingresos": round(_total(cuenta_id, "INGRESO", ini, fin_m), 2),
                "gastos": round(_total(cuenta_id, "GASTO", ini, fin_m), 2),
            })
            mes = ini - timedelta(days=1)
        ctx["ultimos_3_meses"] = meses
    except Exception:
        pass

    return ctx
