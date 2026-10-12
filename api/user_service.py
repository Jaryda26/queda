import bcrypt

from db import obtener_dataframe


def validar_credenciales(email, password):
    """Misma regla que la web: email en minúsculas + bcrypt."""

    df = obtener_dataframe(
        """
        SELECT id, nombre, email, password_hash, cuenta_id, rol_cuenta
        FROM gastos.usuarios
        WHERE email = :email
        """,
        {"email": (email or "").strip().lower()}
    )

    if df.empty:
        return None

    usuario = df.iloc[0].to_dict()

    try:
        ok = bcrypt.checkpw(
            (password or "").encode(),
            str(usuario["password_hash"]).encode()
        )
    except Exception:
        return None

    if not ok:
        return None

    usuario.pop("password_hash", None)
    return usuario


def buscar_usuario_por_id(usuario_id):

    df = obtener_dataframe(
        """
        SELECT id, nombre, email, cuenta_id, rol_cuenta
        FROM gastos.usuarios
        WHERE id = :usuario_id
        """,
        {"usuario_id": usuario_id}
    )

    if df.empty:
        return None

    usuario = df.iloc[0].to_dict()

    # Lo que no se pueda convertir a int (NaN) queda None.
    cid = usuario.get("cuenta_id")
    usuario["cuenta_id"] = None if cid != cid or cid is None else int(cid)
    usuario["id"] = int(usuario["id"])

    return usuario
