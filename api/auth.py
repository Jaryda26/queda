from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import obtener_usuario_actual
from api.schemas import LoginRequest
from api.security import crear_token
from api.user_service import validar_credenciales
from services.billing_service import obtener_plan_actual

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def _info_plan(cuenta_id):
    plan = obtener_plan_actual(cuenta_id)
    if plan is None:
        return {"activa": False, "plan": None,
                "incluye_ia": False, "limite_recordatorios": None}
    return {
        "activa": True,
        "plan": plan.get("plan_nombre"),
        "incluye_ia": plan["incluye_ia"],
        "limite_recordatorios": plan["limite_recordatorios"],
    }


@router.post("/login")
def login(datos: LoginRequest):

    usuario = validar_credenciales(datos.email, datos.password)

    # Mismo mensaje exista o no el correo: no revelar cuentas.
    if not usuario or usuario.get("cuenta_id") is None:
        raise HTTPException(401, "Correo o contraseña incorrectos")

    return {
        "access_token": crear_token({"sub": str(int(usuario["id"]))}),
        "token_type": "bearer",
        "usuario_id": int(usuario["id"]),
        "nombre": usuario["nombre"],
        "suscripcion": _info_plan(int(usuario["cuenta_id"])),
    }


@router.get("/me")
def me(usuario=Depends(obtener_usuario_actual)):
    return {
        "usuario_id": usuario["id"],
        "nombre": usuario["nombre"],
        "email": usuario["email"],
        "rol_cuenta": usuario["rol_cuenta"],
        "suscripcion": _info_plan(usuario["cuenta_id"]),
    }
