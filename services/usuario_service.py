import bcrypt
import hashlib
import secrets
from datetime import datetime, timedelta
from sqlalchemy import text

from db import engine, obtener_dataframe, ejecutar_query
from services.cuenta_service import validar_codigo_invitacion


DIAS_SESION_PERSISTENTE = 30


def crear_token_sesion(usuario_id):
    """
    Genera un token aleatorio para "mantener la sesión iniciada".
    Solo se guarda su HASH en la base (igual que una contraseña,
    aunque con sha256 en vez de bcrypt — no hace falta que sea
    lento, es un token aleatorio de 256 bits, no algo que alguien
    pueda adivinar por fuerza bruta). El token en claro se regresa
    para guardarlo en una cookie del navegador — esa es la única
    copia que existe fuera de la base, y nunca se puede reconstruir
    a partir del hash guardado.
    """

    token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        token.encode()
    ).hexdigest()

    expira = datetime.utcnow() + timedelta(
        days=DIAS_SESION_PERSISTENTE
    )

    ejecutar_query(
        """
        UPDATE gastos.usuarios
        SET token_sesion_hash = :hash, token_sesion_expira = :expira
        WHERE id = :usuario_id
        """,
        {
            "hash": token_hash,
            "expira": expira,
            "usuario_id": usuario_id
        }
    )

    return token


def validar_token_sesion(token):
    """
    Busca al usuario dueño de este token de "mantener sesión" (si
    no expiró). Regresa la misma fila que validar_usuario() — todo
    lo que login_user() necesita — o None si el token es inválido,
    expiró, o ya se invalidó (logout, o alguien pidió "cerrar
    sesión en todos lados").
    """

    if not token:
        return None

    token_hash = hashlib.sha256(
        token.encode()
    ).hexdigest()

    df = obtener_dataframe(
        """
        SELECT *
        FROM gastos.usuarios
        WHERE token_sesion_hash = :hash
        AND token_sesion_expira > :ahora
        """,
        {"hash": token_hash, "ahora": datetime.utcnow()}
    )

    if df.empty:
        return None

    return df.iloc[0]


def invalidar_token_sesion(usuario_id):
    """Cierra la sesión persistente (logout) — borra el token."""

    ejecutar_query(
        """
        UPDATE gastos.usuarios
        SET token_sesion_hash = NULL, token_sesion_expira = NULL
        WHERE id = :usuario_id
        """,
        {"usuario_id": usuario_id}
    )


def registrar_usuario(nombre, email, password, codigo_invitacion=None):

    email_normalizado = email.strip().lower()

    existente = obtener_dataframe(
        "select id from gastos.usuarios where email = :email",
        {"email": email_normalizado}
    )

    if not existente.empty:
        return False, "Ya existe una cuenta con ese correo."

    if not nombre.strip() or not email_normalizado or len(password) < 8:
        return False, "Revisa nombre, correo y una contraseña de al menos 8 caracteres."

    # Si trae un código de invitación válido, se une DIRECTO a esa
    # cuenta (como MIEMBRO) en vez de crear una cuenta individual
    # nueva y tener que pagar por su cuenta para luego unirse.

    cuenta_existente_id = None

    if codigo_invitacion and codigo_invitacion.strip():

        cuenta_existente_id, error = validar_codigo_invitacion(
            codigo_invitacion
        )

        if error:
            return False, error

    hash_password = bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    ).decode()

    nombre_limpio = nombre.strip()

    # Las inserciones van en una sola transacción: si algo falla a
    # la mitad, no queda una cuenta huérfana sin usuario.

    with engine.begin() as conn:

        if cuenta_existente_id is not None:

            cuenta_id = cuenta_existente_id
            rol_cuenta = "MIEMBRO"

        else:

            cuenta_id = conn.execute(
                text(
                    """
                    INSERT INTO gastos.cuentas (nombre, tipo)
                    VALUES (:nombre, 'INDIVIDUAL')
                    RETURNING id
                    """
                ),
                {"nombre": f"Cuenta de {nombre_limpio}"}
            ).fetchone()[0]

            rol_cuenta = "ADMIN"

        conn.execute(
            text(
                """
                INSERT INTO gastos.usuarios
                (nombre, email, password_hash, cuenta_id, rol_cuenta)
                VALUES
                (:nombre, :email, :hash, :cuenta_id, :rol)
                """
            ),
            {
                "nombre": nombre_limpio,
                "email": email_normalizado,
                "hash": hash_password,
                "cuenta_id": cuenta_id,
                "rol": rol_cuenta
            }
        )

        if cuenta_existente_id is None:

            conn.execute(
                text(
                    """
                    INSERT INTO gastos.suscripciones (cuenta_id, status)
                    VALUES (:cuenta_id, 'incomplete')
                    """
                ),
                {"cuenta_id": cuenta_id}
            )

    if cuenta_existente_id is not None:

        return True, (
            "Te uniste a la cuenta familiar correctamente. "
            "Ya puedes iniciar sesión."
        )

    return True, "Cuenta creada correctamente. Ahora elige tu plan para activarla."


def actualizar_nombre_agente(usuario_id, nombre_agente):

    nombre_limpio = nombre_agente.strip()

    if not nombre_limpio:
        return False, "Escribe un nombre."

    if len(nombre_limpio) > 50:
        return False, "El nombre es demasiado largo."

    ejecutar_query(
        """
        UPDATE gastos.usuarios
        SET nombre_agente = :nombre
        WHERE id = :usuario_id
        """,
        {"nombre": nombre_limpio, "usuario_id": usuario_id}
    )

    return True, f"Listo — ahora se llama {nombre_limpio}."


def validar_usuario(email, password):

    email_normalizado = email.strip().lower()

    df = obtener_dataframe(
        "select * from gastos.usuarios where email = :email",
        {"email": email_normalizado}
    )

    if df.empty:
        return None

    usuario = df.iloc[0]

    try:
        if bcrypt.checkpw(
            password.encode(),
            str(usuario["password_hash"]).encode()
        ):
            return usuario

        return None

    except Exception:
        return None
