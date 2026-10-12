# Queda móvil — qué cambió

## API (carpeta `api/`, reemplaza la tuya)
- **Login ahora valida la contraseña (bcrypt)**. Antes entraba cualquiera con solo el correo.
- JWT secret fuera del código: agrega a tu `.env` -> `API_JWT_SECRET=` (python -c "import secrets; print(secrets.token_urlsafe(48))"). Sin esto la API no arranca (a propósito).
- `/dashboard/resumen` antes **no tenía login ni filtro de cuenta** (mostraba datos de todos). Ahora filtra por `cuenta_id`.
- Paywall igual que la web: sin suscripción activa/trialing -> HTTP 402.
- Recordatorios: `PUT /{id}/pagar` ahora hace lo mismo que la web (PAGO crea el gasto, ACTIVIDAD no, recurrentes avanzan fecha); `PUT /{id}/despues`; `DELETE`; crear acepta monto/fecha/frecuencia y respeta el límite del plan (Básico 5).
- Movimientos: `DELETE /{id}` (el saldo se recalcula solo), valida GASTO/INGRESO y monto > 0.
- `/auth/me` ya no recibe el token por URL (iba a quedar en logs); usa `Authorization: Bearer`.

Arrancar (desde la carpeta del proyecto web, donde está `db.py`):
    pip install -r api/requirements_api.txt
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

## Flutter (`queda_mobile_lib_cambios/` -> copia dentro de `queda_mobile/lib/`, sobrescribe)
- `api_service.dart`: cliente HTTP único con token, timeout y errores legibles.
- URL por parámetro, sin editar código:
    Emulador:  flutter run --dart-define=API_URL=http://10.0.2.2:8000
    Teléfono:  flutter run --dart-define=API_URL=http://TU_IP:8000
- `main.dart`: sesión persistente.
- Todos los servicios usan ese cliente (el dashboard/resumen ya manda token).
- Android: si usas http (no https) en `android/app/src/main/AndroidManifest.xml`
  agrega `android:usesCleartextTraffic="true"` en `<application>` (solo desarrollo).
- Producción/iOS: iOS bloquea http; necesitarás la API en HTTPS.
- Borra `screens/voz_screen.dart1.dart` (copia vieja).
