import os

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request

from api.dependencies import es_admin, obtener_usuario_actual
from api.limites import ip_cliente, limitar, olvidar
from api.schemas import LoginRequest, RegistroRequest
from api.security import crear_token
from api.user_service import validar_credenciales
from services.billing_service import obtener_plan_actual, obtener_suscripcion
from services.regalo_service import canjear_codigo, validar_codigo
from services.usuario_service import registrar_usuario

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def _registro_abierto():
    return os.getenv("API_REGISTRO_ABIERTO", "0").strip() == "1"


def info_plan(cuenta_id):
    plan = obtener_plan_actual(cuenta_id)

    if plan is None:
        sub = obtener_suscripcion(cuenta_id)
        vencida = (not sub.empty) and str(sub.iloc[0]["status"]) == "expired"
        return {"activa": False, "plan": None,
                "estado": "vencida" if vencida else "sin_suscripcion",
                "dias_restantes": None, "incluye_ia": False,
                "limite_recordatorios": None}

    estado = str(plan.get("status"))
    dias = None

    fin = plan.get("fin_periodo_actual")

    # Solo las pruebas/regalos (sin Stripe) muestran cuenta regresiva.
    stripe_sub = plan.get("stripe_subscription_id")
    es_regalo = not (isinstance(stripe_sub, str) and stripe_sub.strip())

    if estado == "trialing" and es_regalo and fin is not None and not pd.isna(fin):
        from datetime import datetime, timezone
        ahora = datetime.now(timezone.utc).replace(tzinfo=None)
        delta = pd.Timestamp(fin).to_pydatetime().replace(tzinfo=None) - ahora
        dias = max(delta.days + (1 if delta.seconds > 0 else 0), 0)

    return {
        "activa": True,
        "plan": plan.get("plan_nombre"),
        "estado": estado,
        "dias_restantes": dias,
        "incluye_ia": plan["incluye_ia"],
        "limite_recordatorios": plan["limite_recordatorios"],
    }


def _sesion(usuario):
    return {
        "access_token": crear_token({"sub": str(int(usuario["id"]))}),
        "token_type": "bearer",
        "usuario_id": int(usuario["id"]),
        "nombre": usuario["nombre"],
        "suscripcion": info_plan(int(usuario["cuenta_id"])),
    }


@router.post("/login")
def login(datos: LoginRequest, request: Request):

    ip = ip_cliente(request)
    clave = f"login:{ip}:{datos.email.strip().lower()}"
    limitar(clave, 8, 600, "Demasiados intentos fallidos.")
    limitar(f"login-ip:{ip}", 40, 600, "Demasiados intentos desde este dispositivo.")

    usuario = validar_credenciales(datos.email, datos.password)

    # Mismo mensaje exista o no el correo: no revelar cuentas.
    if not usuario or usuario.get("cuenta_id") is None:
        raise HTTPException(401, "Correo o contraseña incorrectos")

    olvidar(clave)

    return _sesion(usuario)


@router.post("/registro")
def registro(datos: RegistroRequest, request: Request):
    """
    Crea la cuenta desde la app. Mientras la app esté en pruebas
    (API_REGISTRO_ABIERTO != 1) hace falta un código de regalo o de
    invitación familiar. Con código de regalo la cuenta nace con
    prueba activa y entra directo.
    """

    limitar(f"registro:{ip_cliente(request)}", 5, 3600,
            "Demasiados registros desde este dispositivo.")

    codigo = (datos.codigo or "").strip()
    regalo = None

    if codigo:
        regalo, error = validar_codigo(codigo)
        if error:
            raise HTTPException(422, error)

    if not codigo and not _registro_abierto():
        raise HTTPException(
            403,
            "El registro está en pruebas: necesitas un código de regalo "
            "o de invitación.",
        )

    # Un código que no es de regalo se trata como invitación familiar
    # (registrar_usuario lo valida y avisa si es inválido).
    ok, mensaje = registrar_usuario(
        datos.nombre,
        datos.email,
        datos.password,
        None if regalo else (codigo or None),
    )

    if not ok:
        raise HTTPException(422, mensaje)

    usuario = validar_credenciales(datos.email, datos.password)

    if not usuario or usuario.get("cuenta_id") is None:
        raise HTTPException(500, "La cuenta se creó pero no pudo iniciar sesión.")

    aviso = mensaje

    if regalo:
        ok_canje, msg_canje = canjear_codigo(
            int(usuario["cuenta_id"]), int(usuario["id"]), codigo
        )
        # Si perdió la carrera por el último uso, la cuenta existe sin
        # prueba: se le dice claro en vez de fingir que quedó activa.
        aviso = msg_canje if ok_canje else (
            "Tu cuenta se creó, pero el código ya no estaba disponible. "
            "Pide uno nuevo y canjéalo desde la app."
        )

    sesion = _sesion(usuario)
    sesion["mensaje"] = aviso
    return sesion


@router.get("/me")
def me(usuario=Depends(obtener_usuario_actual)):
    return {
        "usuario_id": usuario["id"],
        "nombre": usuario["nombre"],
        "email": usuario["email"],
        "rol_cuenta": usuario["rol_cuenta"],
        "es_admin": es_admin(usuario),
        "suscripcion": info_plan(usuario["cuenta_id"]),
    }
