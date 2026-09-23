import bcrypt
from db import ejecutar_query, obtener_dataframe


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

    ejecutar_query(
        """
        INSERT INTO gastos.usuarios (nombre, email, password_hash)
        VALUES (:nombre, :email, :hash)
        """,
        {
            "nombre": nombre.strip(),
            "email": email_normalizado,
            "hash": hash_password
        }
    )

    return True, "Cuenta creada correctamente."


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
