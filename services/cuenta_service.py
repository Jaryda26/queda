import random
import string

from db import obtener_dataframe, ejecutar_query


def generar_codigo_invitacion():

    return "".join(
        random.choices(
            string.ascii_uppercase + string.digits,
            k=6
        )
    )


def obtener_miembros(cuenta_id):

    return obtener_dataframe(
        """
        SELECT id, nombre, email, rol_cuenta
        FROM gastos.usuarios
        WHERE cuenta_id = :cuenta_id
        ORDER BY rol_cuenta DESC, nombre
        """,
        {"cuenta_id": cuenta_id}
    )


def obtener_o_crear_codigo(cuenta_id):

    df = obtener_dataframe(
        """
        SELECT codigo_invitacion
        FROM gastos.cuentas
        WHERE id = :cuenta_id
        """,
        {"cuenta_id": cuenta_id}
    )

    if df.empty:
        return None

    codigo_actual = df.iloc[0]["codigo_invitacion"]

    if codigo_actual:
        return codigo_actual

    nuevo_codigo = generar_codigo_invitacion()

    ejecutar_query(
        """
        UPDATE gastos.cuentas
        SET codigo_invitacion = :codigo
        WHERE id = :cuenta_id
        """,
        {"codigo": nuevo_codigo, "cuenta_id": cuenta_id}
    )

    return nuevo_codigo


def limite_miembros_cuenta(cuenta_id):
    """
    Límite de miembros según el plan activo de la cuenta.
    Si no tiene suscripción activa, se asume 1 (no puede crecer
    hasta que se suscriba).
    """

    df = obtener_dataframe(
        """
        SELECT p.limite_miembros
        FROM gastos.suscripciones s
        JOIN gastos.planes p ON p.id = s.plan_id
        WHERE s.cuenta_id = :cuenta_id
        AND s.status IN ('active', 'trialing')
        ORDER BY s.id DESC
        LIMIT 1
        """,
        {"cuenta_id": cuenta_id}
    )

    if df.empty:
        return 1

    return int(df.iloc[0]["limite_miembros"])


def unirse_a_cuenta(usuario_id, codigo):
    """
    Mueve a este usuario a la cuenta dueña del código. Su historial
    financiero anterior se queda en su cuenta vieja (no se mezcla
    automáticamente) — deja de ser visible para él, pero no se
    borra.
    """

    codigo_normalizado = codigo.strip().upper()

    cuenta_df = obtener_dataframe(
        """
        SELECT id
        FROM gastos.cuentas
        WHERE codigo_invitacion = :codigo
        """,
        {"codigo": codigo_normalizado}
    )

    if cuenta_df.empty:
        return False, "Código de invitación inválido."

    cuenta_id = int(cuenta_df.iloc[0]["id"])

    miembros_df = obtener_miembros(cuenta_id)

    limite = limite_miembros_cuenta(cuenta_id)

    if len(miembros_df) >= limite:
        return False, (
            "Esa cuenta ya alcanzó su límite de miembros "
            "para su plan actual."
        )

    ejecutar_query(
        """
        UPDATE gastos.usuarios
        SET cuenta_id = :cuenta_id, rol_cuenta = 'MIEMBRO'
        WHERE id = :usuario_id
        """,
        {"cuenta_id": cuenta_id, "usuario_id": usuario_id}
    )

    return True, "Te uniste a la cuenta correctamente."
