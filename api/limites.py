"""
Límite de intentos en memoria (una instancia de la API). Frena adivinar
contraseñas y registros masivos; se reinicia si el servidor se reinicia.
"""

import threading
import time

from fastapi import HTTPException, Request

_lock = threading.Lock()
_intentos = {}


def ip_cliente(request: Request):
    return request.client.host if request.client else "desconocida"


def limitar(clave, maximo, ventana_seg, mensaje):
    """Cuenta un intento; lanza 429 si se pasó del máximo en la ventana."""

    ahora = time.time()

    with _lock:
        recientes = [t for t in _intentos.get(clave, []) if ahora - t < ventana_seg]

        if len(recientes) >= maximo:
            _intentos[clave] = recientes
            espera = int(ventana_seg - (ahora - recientes[0])) + 1
            raise HTTPException(
                429, f"{mensaje} Intenta de nuevo en {max(espera // 60, 1)} min."
            )

        recientes.append(ahora)
        _intentos[clave] = recientes

        # Limpieza ocasional para que el diccionario no crezca sin fin.
        if len(_intentos) > 5000:
            for k in list(_intentos):
                if not [t for t in _intentos[k] if ahora - t < ventana_seg]:
                    _intentos.pop(k, None)


def olvidar(clave):
    with _lock:
        _intentos.pop(clave, None)
