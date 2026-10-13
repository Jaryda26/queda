import os

from fastapi import Depends, Header, HTTPException

from api.security import validar_token
from api.user_service import buscar_usuario_por_id
from services.billing_service import (
    obtener_plan_actual,
    tiene_suscripcion_activa,
)


def obtener_usuario_actual(authorization: str = Header(None)):
    """Cualquier usuario con token válido (aunque no tenga plan)."""

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token requerido")

    payload = validar_token(authorization[7:].strip())

    if not payload or "sub" not in payload:
        raise HTTPException(401, "Token inválido o vencido")

    usuario = buscar_usuario_por_id(int(payload["sub"]))

    if not usuario or usuario["cuenta_id"] is None:
        raise HTTPException(401, "Usuario no encontrado")

    return usuario


def usuario_con_plan(authorization: str = Header(None)):
    """Igual que la web: sin suscripción activa/trialing no hay datos."""

    usuario = obtener_usuario_actual(authorization)

    if not tiene_suscripcion_activa(usuario["cuenta_id"]):
        raise HTTPException(
            402,
            "Tu cuenta no tiene una suscripción activa. "
            "Actívala desde la web."
        )

    return usuario


def exigir_ia(usuario):
    plan = obtener_plan_actual(usuario["cuenta_id"])
    if plan is None or not plan.get("incluye_ia", False):
        raise HTTPException(403, "Tu plan no incluye IA.")


def _admins():
    return {
        e.strip().lower()
        for e in os.getenv("ADMIN_EMAILS", "").split(",")
        if e.strip()
    }


def es_admin(usuario):
    return str(usuario.get("email", "")).strip().lower() in _admins()


def exigir_admin(usuario=Depends(obtener_usuario_actual)):
    """Solo los correos de ADMIN_EMAILS (variable de entorno del servidor)."""

    if not es_admin(usuario):
        raise HTTPException(403, "Solo para administradores.")

    return usuario
