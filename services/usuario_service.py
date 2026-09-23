import bcrypt
from sqlalchemy import text

from db import engine, obtener_dataframe


def registrar_usuario(nombre, email, password):

    email_normalizado = email.strip().lower()

    existente = obtener_dataframe(
        "select id from gastos.usuarios where email = :email",
        {"email": email_normalizado}
    )

    if not existente.empty:
        return False, "Ya existe una cuenta con ese correo."

    if not nombre.strip() or not email_normalizado or len(password) < 8:
        return False, "Revisa nombre, correo y una contraseña de al menos 8 caracteres."

    hash_password = bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    ).decode()

    nombre_limpio = nombre.strip()

    # Un usuario nuevo siempre arranca con su propia cuenta
    # INDIVIDUAL (puede unirse a una cuenta FAMILIAR después con
    # un código de invitación — ver services/cuenta_service.py).
    # Las 3 inserciones van en una sola transacción: si algo falla
    # a la mitad, no queda una cuenta huérfana sin usuario.

    with engine.begin() as conn:

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

        conn.execute(
            text(
                """
                INSERT INTO gastos.usuarios
                (nombre, email, password_hash, cuenta_id, rol_cuenta)
                VALUES
                (:nombre, :email, :hash, :cuenta_id, 'ADMIN')
                """
            ),
            {
                "nombre": nombre_limpio,
                "email": email_normalizado,
                "hash": hash_password,
                "cuenta_id": cuenta_id
            }
        )

        conn.execute(
            text(
                """
                INSERT INTO gastos.suscripciones (cuenta_id, status)
                VALUES (:cuenta_id, 'incomplete')
                """
            ),
            {"cuenta_id": cuenta_id}
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
