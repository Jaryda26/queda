from fastapi import Header, HTTPException

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
