import bcrypt
from sqlalchemy import text

from db import engine, obtener_dataframe
from services.cuenta_service import validar_codigo_invitacion


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
