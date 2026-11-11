# Formulario web de catalogación – cómo publicarlo

Archivos que se suben a GitHub: `app_web.py`, `requirements.txt`, `logo.png`, `.streamlit/config.toml`, `.gitignore`.
**Nunca** suba el archivo `.json` de credenciales ni `secretos_para_streamlit.txt`.

## A. Google Sheets y cuenta de servicio
1. En sheets.google.com cree una hoja nueva: "Solicitudes catalogación MMG". Copie su enlace.
2. En console.cloud.google.com: cree un proyecto → APIs y servicios → Biblioteca → habilite **Google Sheets API** y **Google Drive API**.
3. IAM y administración → Cuentas de servicio → Crear ("formulario-catalogacion") → Listo.
   Entre a la cuenta → Claves → Agregar clave → JSON. Se descarga un archivo .json.
4. Guarde el .json en `C:\CatalogacionApp\Credenciales\` (solo en su PC).
5. Ejecute `GENERAR_SECRETOS.bat` (carpeta de la app): arrastre el .json, pegue el enlace de la hoja y elija un código de acceso.
6. En la hoja de Google: Compartir → pegue el correo de la cuenta de servicio que mostró el paso 5 → Editor.

## B. GitHub (repositorio privado)
1. github.com → New repository → nombre `formulario-catalogacion` → **Private** → Create.
2. "uploading an existing file" → arrastre los archivos de la carpeta FormularioWeb (incluida la carpeta .streamlit) → Commit.

## C. Streamlit Community Cloud
1. share.streamlit.io → ingrese con GitHub → autorice el acceso a repositorios privados.
2. Create app → repositorio `formulario-catalogacion`, rama `main`, archivo `app_web.py`.
3. Advanced settings → Secrets → pegue todo el texto de `secretos_para_streamlit.txt` → Deploy.
4. Copie el enlace (https://….streamlit.app) y envíelo a los socios junto con el código de acceso.

## D. Conectar con la base (PC de Planeamiento)
1. Ejecute `INSTALAR.bat` otra vez (instala gspread).
2. App → Seguimiento y tablero → Ubicación de la base → pegue el enlace de la hoja y la ruta del .json → Guardar.
3. `ACTUALIZAR_BASE.bat` (o la tarea programada cada 30 min) pasa las solicitudes nuevas a la base.
