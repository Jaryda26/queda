"""
Pruebas y regalos de suscripción.

Un regalo es una suscripción 'trialing' SIN Stripe, con fecha de fin en
fin_periodo_actual (billing_service la da por vencida cuando pasa).
Se otorga de dos formas:
  - Código de regalo (lo crea el administrador y se lo pasa a la persona).
  - Directo a un correo ya registrado (regalar_a_email).
"""

import secrets
from datetime import datetime, timedelta, timezone

import pandas as pd

from db import ejecutar_query, ejecutar_query_retornando, obtener_dataframe

# Sin 0/O/1/I/L para que el código se pueda dictar por teléfono.
_ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

DIAS_MAX = 365


def _ahora():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalizar_codigo(codigo):
    return "".join((codigo or "").upper().split())


def _generar_codigo():
    g = "".join(secrets.choice(_ALFABETO) for _ in range(8))
    return f"QUEDA-{g[:4]}-{g[4:]}"


def _plan(plan_slug):
    df = obtener_dataframe(
        "SELECT id, slug, nombre FROM gastos.planes WHERE slug = :s AND activo = TRUE",
        {"s": plan_slug},
    )
    return None if df.empty else df.iloc[0].to_dict()


# ------------------------------------------------------------------
# Otorgar días a una cuenta
# ------------------------------------------------------------------

def otorgar_dias(cuenta_id, dias, plan_slug="individual"):
    """
    Pone/extiende una prueba. Regresa (ok, mensaje, fin_datetime|None).
    - Cuenta con suscripción de pago activa: no se toca.
    - Cuenta con prueba vigente: se SUMAN los días al final actual.
    - Cuenta sin suscripción, vencida o 'incomplete': empieza hoy.
    """

    if not (1 <= int(dias) <= DIAS_MAX):
        return False, f"Los días deben estar entre 1 y {DIAS_MAX}.", None

    plan = _plan(plan_slug)

    if plan is None:
        return False, "Ese plan no existe.", None

    df = obtener_dataframe(
        """
        SELECT id, status, stripe_subscription_id, fin_periodo_actual
        FROM gastos.suscripciones
        WHERE cuenta_id = :c
        ORDER BY id DESC
        LIMIT 1
        """,
        {"c": cuenta_id},
    )

    ahora = _ahora()
    base = ahora

    if not df.empty:

        fila = df.iloc[0]
        stripe_sub = fila["stripe_subscription_id"]
        tiene_stripe = isinstance(stripe_sub, str) and stripe_sub.strip() != ""

        if str(fila["status"]) == "active" and tiene_stripe:
            return False, "Esa cuenta ya tiene una suscripción de pago activa.", None

        fin_actual = fila["fin_periodo_actual"]

        if (
            str(fila["status"]) == "trialing"
            and not pd.isna(fin_actual)
            and pd.Timestamp(fin_actual).to_pydatetime().replace(tzinfo=None) > ahora
        ):
            base = pd.Timestamp(fin_actual).to_pydatetime().replace(tzinfo=None)

    fin = base + timedelta(days=int(dias))

    if df.empty:
        ejecutar_query(
            """
            INSERT INTO gastos.suscripciones
                (cuenta_id, plan_id, status, fecha_inicio, fin_periodo_actual)
            VALUES (:c, :p, 'trialing', :ini, :fin)
            """,
            {"c": cuenta_id, "p": int(plan["id"]), "ini": ahora, "fin": fin},
        )
    else:
        ejecutar_query(
            """
            UPDATE gastos.suscripciones
            SET plan_id = :p, status = 'trialing',
                fecha_inicio = COALESCE(fecha_inicio, :ini),
                fin_periodo_actual = :fin,
                cancelar_al_final_periodo = FALSE,
                fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE id = :id
            """,
            {"id": int(df.iloc[0]["id"]), "p": int(plan["id"]),
             "ini": ahora, "fin": fin},
        )

    return True, f"Plan {plan['nombre']} activo hasta el {fin:%d/%m/%Y}.", fin


def regalar_a_email(email, dias, plan_slug="individual"):
    """El administrador regala días a alguien que YA tiene cuenta."""

    df = obtener_dataframe(
        "SELECT cuenta_id FROM gastos.usuarios WHERE email = :e",
        {"e": (email or "").strip().lower()},
    )

    if df.empty or pd.isna(df.iloc[0]["cuenta_id"]):
        return False, "No hay ninguna cuenta con ese correo.", None

    return otorgar_dias(int(df.iloc[0]["cuenta_id"]), dias, plan_slug)


# ------------------------------------------------------------------
# Códigos de regalo
# ------------------------------------------------------------------

def crear_codigo(admin_id, dias=30, plan_slug="individual", usos_max=1,
                 vence_en_dias=None, nota=None):
    """Regresa (codigo|None, mensaje)."""

    dias = int(dias)
    usos_max = int(usos_max)

    if not (1 <= dias <= DIAS_MAX):
        return None, f"Los días deben estar entre 1 y {DIAS_MAX}."

    if not (1 <= usos_max <= 100):
        return None, "Los usos deben estar entre 1 y 100."

    if _plan(plan_slug) is None:
        return None, "Ese plan no existe."

    vence = None
    if vence_en_dias:
        vence = _ahora() + timedelta(days=int(vence_en_dias))

    for _ in range(5):  # reintento ante choque de código (casi imposible)
        codigo = _generar_codigo()
        fila = ejecutar_query_retornando(
            """
            INSERT INTO gastos.codigos_regalo
                (codigo, dias, plan_slug, usos_max, vence, nota, creado_por)
            VALUES (:cod, :dias, :plan, :usos, :vence, :nota, :admin)
            ON CONFLICT (codigo) DO NOTHING
            RETURNING id
            """,
            {"cod": codigo, "dias": dias, "plan": plan_slug, "usos": usos_max,
             "vence": vence, "nota": (nota or "").strip()[:200] or None,
             "admin": admin_id},
        )
        if fila:
            return codigo, "Código creado."

    return None, "No se pudo generar un código único, intenta de nuevo."


def listar_codigos():
    df = obtener_dataframe(
        """
        SELECT id, codigo, dias, plan_slug, usos_max, usos, vence, activo, nota,
               fecha_creacion
        FROM gastos.codigos_regalo
        ORDER BY id DESC
        LIMIT 100
        """
    )
    ahora = _ahora()
    salida = []
    for _, f in df.iterrows():
        vence = None if pd.isna(f["vence"]) else pd.Timestamp(f["vence"]).to_pydatetime()
        vencido = vence is not None and vence < ahora
        agotado = int(f["usos"]) >= int(f["usos_max"])
        salida.append({
            "id": int(f["id"]),
            "codigo": str(f["codigo"]),
            "dias": int(f["dias"]),
            "plan_slug": str(f["plan_slug"]),
            "usos_max": int(f["usos_max"]),
            "usos": int(f["usos"]),
            "vence": vence.strftime("%Y-%m-%d") if vence else None,
            "nota": None if pd.isna(f["nota"]) else str(f["nota"]),
            "estado": (
                "desactivado" if not bool(f["activo"])
                else "vencido" if vencido
                else "agotado" if agotado
                else "disponible"
            ),
        })
    return salida


def desactivar_codigo(codigo_id):
    r = ejecutar_query(
        "UPDATE gastos.codigos_regalo SET activo = FALSE WHERE id = :id",
        {"id": int(codigo_id)},
    )
    return bool(getattr(r, "rowcount", 0))


def validar_codigo(codigo):
    """
    SIN consumirlo. Regresa (fila_dict|None, error|None). error=None y
    fila=None significa "no es un código de regalo" (puede ser de
    invitación familiar).
    """

    cod = normalizar_codigo(codigo)

    df = obtener_dataframe(
        """
        SELECT id, codigo, dias, plan_slug, usos_max, usos, vence, activo
        FROM gastos.codigos_regalo
        WHERE codigo = :c
        """,
        {"c": cod},
    )

    if df.empty:
        return None, None

    f = df.iloc[0].to_dict()

    if not bool(f["activo"]):
        return None, "Ese código ya no está activo."

    if not pd.isna(f["vence"]) and pd.Timestamp(f["vence"]).to_pydatetime().replace(tzinfo=None) < _ahora():
        return None, "Ese código ya venció."

    if int(f["usos"]) >= int(f["usos_max"]):
        return None, "Ese código ya se usó."

    return f, None


def canjear_codigo(cuenta_id, usuario_id, codigo):
    """Consume el código y otorga los días. Regresa (ok, mensaje)."""

    fila, error = validar_codigo(codigo)

    if error:
        return False, error

    if fila is None:
        return False, "Código no válido."

    ya = obtener_dataframe(
        "SELECT 1 FROM gastos.canjes_regalo WHERE codigo_id = :i AND cuenta_id = :c",
        {"i": int(fila["id"]), "c": cuenta_id},
    )

    if not ya.empty:
        return False, "Tu cuenta ya canjeó ese código."

    # 1) Se reserva el uso de forma atómica: dos canjes simultáneos no
    #    pueden pasar del límite de usos.
    tomado = ejecutar_query_retornando(
        """
        UPDATE gastos.codigos_regalo
        SET usos = usos + 1
        WHERE id = :id AND activo = TRUE AND usos < usos_max
          AND (vence IS NULL OR vence > :ahora)
        RETURNING id
        """,
        {"id": int(fila["id"]), "ahora": _ahora()},
    )

    if not tomado:
        return False, "Ese código ya se usó."

    # 2) Se otorgan los días. Si no procede (p. ej. la cuenta ya paga),
    #    se devuelve el uso para no gastar el código en vano.
    ok, mensaje, _ = otorgar_dias(
        cuenta_id, int(fila["dias"]), str(fila["plan_slug"])
    )

    if not ok:
        ejecutar_query(
            "UPDATE gastos.codigos_regalo SET usos = usos - 1 WHERE id = :id",
            {"id": int(fila["id"])},
        )
        return False, mensaje

    ejecutar_query(
        """
        INSERT INTO gastos.canjes_regalo (codigo_id, cuenta_id, usuario_id)
        VALUES (:i, :c, :u)
        ON CONFLICT (codigo_id, cuenta_id) DO NOTHING
        """,
        {"i": int(fila["id"]), "c": cuenta_id, "u": usuario_id},
    )

    return True, mensaje
