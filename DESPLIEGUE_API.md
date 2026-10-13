# Publicar la API de Queda (Render + HTTPS)

Archivos nuevos en la raíz del proyecto: `Dockerfile`, `.dockerignore`, `requirements_api.txt`.
(El `requirements.txt` de la raíz sigue siendo el de Streamlit; no lo toques.)

## 1. Subir a git
    git add Dockerfile .dockerignore requirements_api.txt api services
    git commit -m "API lista para desplegar"
    git push
`.env` NO se sube (ya está en .gitignore y en .dockerignore). Los secretos van en Render.

## 2. Supabase: cadena de conexión
Render solo habla IPv4. Si tu DATABASE_URL es la conexión directa (db.xxxx.supabase.co) puede fallar con
"Network is unreachable". Usa la del **Session pooler**:
Supabase → Connect → "Session pooler" → copia la URI (puerto 5432).
Si la contraseña tiene caracteres como @ # / : ?, deben ir codificados (ej. @ = %40).

## 3. Render
1. render.com → New → **Web Service** → conecta el repo.
2. Language/Runtime: **Docker** (detecta el Dockerfile). Branch: main.
3. Health Check Path: `/health`
4. Instance type: **Starter** (US$7/mes). El plan gratis se duerme a los 15 min y el primer
   request tarda ~1 min: la app mostraría "Sin conexión" al abrirla.
5. Environment Variables:
       DATABASE_URL            = (cadena del pooler)
       API_JWT_SECRET          = (NUEVO, ver abajo)
       AZURE_OPENAI_ENDPOINT   = ...
       AZURE_OPENAI_KEY        = ...
       AZURE_OPENAI_DEPLOYMENT = ...
   Genera el secreto así (mínimo 32 caracteres):
       python -c "import secrets; print(secrets.token_urlsafe(48))"
   Pégalos sin comillas y sin espacios al final.
6. Create Web Service. Al terminar tendrás `https://TU-SERVICIO.onrender.com`.

## 4. Verificar
- `https://TU-SERVICIO.onrender.com/health` -> {"status":"ok"}
- Si falla, revisa Render → Logs (error de conexión a la base o variable faltante).

## 5. APK apuntando a la API publicada
    flutter build apk --release --dart-define=API_URL=https://TU-SERVICIO.onrender.com
Con HTTPS ya puedes quitar `android:usesCleartextTraffic="true"` del AndroidManifest.
Al cambiar API_JWT_SECRET se cierra la sesión en los teléfonos: hay que volver a entrar.
