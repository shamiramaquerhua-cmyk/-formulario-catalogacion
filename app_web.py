r"""
FORMULARIO WEB DE SOLICITUD DE CATALOGACIÓN (Streamlit Community Cloud)

- No lee la base de MMG: solo recibe solicitudes.
- Cada envío se agrega a Google Sheets (pestaña "Solicitudes"); los archivos adjuntos van a la pestaña "Adjuntos".
- La marca del equipo sale de la pestaña "Equipos" (la llena la PC de Planeamiento desde la hoja Fabricante de la base).
- En la PC de Planeamiento, ACTUALIZAR_BASE.bat descarga lo nuevo a la base y los adjuntos a Base\Adjuntos.
"""
import base64
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

APP = Path(__file__).parent
LOGO = APP / "logo.png"
st.set_page_config(page_title="Solicitud de catalogación | Las Bambas",
                   page_icon=str(LOGO) if LOGO.exists() else None, layout="wide")

ROJO, NARANJA, AZUL, VERDE = "#EE2724", "#F78F1E", "#18A6DE", "#38B549"

AREAS = ["Palas", "Perforadoras", "Cargadores"]
# Marca que ve el contratista -> nombre que va al texto de catalogación y a la base
MARCAS = {"KOMATSU": "KOMATSU", "P&H": "P&H", "CAT": "CAT", "EPIROC": "EPIROC", "MTU": "MTU", "OTROS": ""}
EQUIV_MARCA = {"KMMP": "KOMATSU", "KOMATSU": "KOMATSU", "P&H": "P&H", "CAT": "CAT", "EPIROC": "EPIROC", "MTU": "MTU"}
# Base de equipos por defecto (hoja "Fabricante" de la base). Equipo -> marca
EQUIPOS_DEF = {"SH001": "CAT", "SH002": "CAT", "SH003": "P&H", "SH004": "P&H", "SH005": "P&H", "SH011": "CAT",
               "SH012": "CAT", "SH013": "CAT", "EX020": "KOMATSU", "LD001": "P&H", "TD002": "P&H", "TD003": "P&H",
               "TD004": "P&H", "TD005": "CAT", "TD006": "CAT", "TD007": "CAT", "TD008": "P&H", "TD009": "EPIROC",
               "TD010": "EPIROC", "TD013": "CAT", "TD014": "EPIROC"}
UNIDADES = ["EA", "KIT", "M", "CM", "DM", "FT", "IN", "ROLLO", "PAC"]
BLOQUEADOS = {".exe", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".msi", ".scr", ".dll", ".com", ".jar", ".lnk", ".reg"}
MAX_MB = 10


def area_de(info):
    """Área según la flota del equipo (Palas incluye excavadoras; Cargadores, los LD)."""
    f = (info.get("Flota", "") + " " + info.get("Clase de flota", "")).upper()
    if "PALAS" in f or "EXCAVADORA" in f:
        return "Palas"
    if "PERFORADORA" in f:
        return "Perforadoras"
    if "CARGADOR" in f:
        return "Cargadores"
    return ""
HOJA, HOJA_ADJ, HOJA_EQ = "Solicitudes", "Adjuntos", "Equipos"
COLUMNAS = ["Código solicitud", "Fecha solicitud", "Solicitante", "Área", "Equipo", "Marca equipo", "Flota",
            "Clase de flota", "Modelo", "Nombre del equipo", "Ítem", "OT",
            "NP solicitado", "Descripción", "Vendor", "Cant.", "UdM", "Texto para catalogar", "Proyecto / Motivo", "Adjuntos"]
COL_ADJ = ["Código solicitud", "Archivo", "Parte", "Total", "Datos"]
TROZO = 45000          # caracteres por celda (límite de Google Sheets: 50 000)
ZONA = ZoneInfo("America/Lima")
VERIFICA = False       # la versión web no consulta la base

# ------------------------------------------------------------------ estilo
st.markdown(f"""
<style>
.block-container {{padding-top: 1.2rem; max-width: 1150px;}}
.cab {{display:flex; align-items:center; gap:22px; border:1px solid #E6E6E6; border-top:4px solid {ROJO};
       border-radius:6px; padding:16px 22px; margin-bottom:6px;}}
.cab img {{height:54px; background:#fff; padding:4px 8px; border-radius:4px;}}
.cab h1 {{margin:0; padding:0; font-size:1.5rem;}}
.cab p {{margin:2px 0 0; opacity:.7;}}
.franja {{display:flex; height:3px; margin-bottom:16px;}} .franja div {{flex:1;}}
.paso {{display:flex; align-items:center; gap:10px; margin:18px 0 8px; border-bottom:1px solid #E6E6E6; padding-bottom:6px;}}
.paso span {{background:{ROJO}; color:#fff; border-radius:3px; min-width:26px; height:26px; display:inline-flex;
            align-items:center; justify-content:center; font-weight:700;}}
.paso b {{text-transform:uppercase; letter-spacing:.5px;}}
input[aria-label="Solicitante *"] {{text-transform:uppercase;}}
</style>""", unsafe_allow_html=True)
logo = f'<img src="data:image/png;base64,{base64.b64encode(LOGO.read_bytes()).decode()}">' if LOGO.exists() else ""
st.markdown(f"""<div class="cab">{logo}<div><h1>Solicitud de catalogación de materiales</h1>
<p>Superintendencia de Mantenimiento Mina · Planeamiento y Confiabilidad Mina</p></div></div>
<div class="franja">{"".join(f'<div style="background:{c}"></div>' for c in (ROJO, NARANJA, AZUL, VERDE, "#006838"))}</div>""",
            unsafe_allow_html=True)


def paso(n, txt):
    st.markdown(f'<div class="paso"><span>{n}</span><b>{txt}</b></div>', unsafe_allow_html=True)


def texto(desc, np_, marca):
    return ",".join(x for x in (desc, np_, marca) if x)


def ahora_local():
    return datetime.now(ZONA)


def estado_np(np_):
    return "nuevo", ""


# ------------------------------------------------------------------ código de acceso
clave = str(st.secrets.get("clave_acceso", "") or "")
if clave and not st.session_state.get("ok_clave"):
    st.write("Ingrese el código de acceso que le entregó Planeamiento y Confiabilidad Mina.")
    c = st.text_input("Código de acceso", type="password")
    if st.button("Ingresar", type="primary"):
        if c.strip() == clave:
            st.session_state["ok_clave"] = True; st.rerun()
        else:
            st.error("Código incorrecto.")
    st.stop()


# ------------------------------------------------------------------ Google Sheets
@st.cache_resource(show_spinner=False)
def libro():
    import gspread
    gc = gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
    return gc.open_by_url(st.secrets["hoja_url"])


def pestaña(nombre, columnas):
    import gspread
    lb = libro()
    try:
        ws = lb.worksheet(nombre)
    except gspread.WorksheetNotFound:
        ws = lb.add_worksheet(nombre, rows=1000, cols=len(columnas))
    if ws.row_values(1)[:len(columnas)] != columnas:
        ws.update([columnas], "A1")
    return ws


@st.cache_data(ttl=600, show_spinner=False)
def _equipos_hoja():
    """Lee la pestaña Equipos. Si falla, lanza error (y no queda guardado en caché)."""
    filas = libro().worksheet(HOJA_EQ).get_all_records(numericise_ignore=["all"])
    d = {str(r["Equipo"]).strip().upper(): {k: str(r.get(k, "")).strip() for k in
         ("Marca", "Flota", "Clase de flota", "Modelo", "Nombre del equipo")} for r in filas if str(r.get("Equipo", "")).strip()}
    if not d:
        raise ValueError("pestaña Equipos vacía")
    return d


def equipos():
    """Equipo -> datos, desde la pestaña Equipos (la actualiza la PC de Planeamiento con ACTUALIZAR_BASE).
    Si todavía no existe, usa la lista corta por defecto y vuelve a intentar en la siguiente carga."""
    try:
        return _equipos_hoja()
    except Exception:
        return {e: {"Marca": m} for e, m in EQUIPOS_DEF.items()}


def guardar(codigo, salida, adjuntos):
    filas = salida[COLUMNAS].astype(object).where(salida[COLUMNAS].notna(), "").values.tolist()
    filas = [[v.item() if hasattr(v, "item") else v for v in f] for f in filas]
    pestaña(HOJA, COLUMNAS).append_rows(filas, value_input_option="RAW")
    if adjuntos:
        ws = pestaña(HOJA_ADJ, COL_ADJ)
        for f in adjuntos:
            b64 = base64.b64encode(f.getvalue()).decode()
            trozos = [b64[i:i + TROZO] for i in range(0, len(b64), TROZO)] or [""]
            filas = [[codigo, f.name, i + 1, len(trozos), tr] for i, tr in enumerate(trozos)]
            for i in range(0, len(filas), 30):            # lotes de ~1.3 MB
                ws.append_rows(filas[i:i + 30], value_input_option="RAW")


# ================================================================== formulario
if st.session_state.get("enviado"):
    st.success(st.session_state["enviado"])
    if st.button("Registrar otra solicitud"):
        st.session_state.pop("enviado"); st.session_state["tabla_v"] = st.session_state.get("tabla_v", 0) + 1
        st.rerun()
    st.stop()

# ---------------------------------------------------------------- 1. datos
paso(1, "Datos")
c1, c2 = st.columns([2, 1])
solicitante = c1.text_input("Solicitante *", placeholder="NOMBRES Y APELLIDOS",
                            help="Se guarda en mayúsculas.").strip().upper()
EQ = equipos()
equipo = c2.selectbox("Equipo *", sorted(EQ) + ["Otro"], help="Escriba el código para buscarlo (ej.: SH005)")
info = dict(EQ.get(equipo, {}))
d1, d2, d3, d4 = st.columns(4)
if equipo == "Otro":
    equipo = c2.text_input("Indique el equipo").strip().upper()
    info = {"Flota": d1.text_input("Flota", key="fl_otro").strip().upper(),
            "Modelo": d2.text_input("Modelo", key="mo_otro").strip().upper(),
            "Marca": d3.text_input("Marca", key="ma_otro").strip().upper(),
            "Nombre del equipo": d4.text_input("Nombre del equipo", key="no_otro").strip()}
else:
    d1.text_input("Flota", info.get("Flota", ""), disabled=True, key=f"fl_{equipo}")
    d2.text_input("Modelo", info.get("Modelo", ""), disabled=True, key=f"mo_{equipo}")
    d3.text_input("Marca", info.get("Marca", ""), disabled=True, key=f"ma_{equipo}")
    d4.text_input("Nombre del equipo", info.get("Nombre del equipo", ""), disabled=True, key=f"no_{equipo}")
marca = EQUIV_MARCA.get(info.get("Marca", "").upper(), info.get("Marca", "").upper())
area = area_de(info) or "Otros"

# ---------------------------------------------------------------- 2. números de parte
paso(2, "Números de parte")
st.caption("Una fila por N° de parte; una OT puede tener muchos NP. «Marca NP» vacía = marca del equipo.")
vacia = pd.DataFrame({"Ítem": list(range(1, 6)), "OT": [""] * 5, "N° de parte": [""] * 5, "Descripción": [""] * 5,
                      "Marca NP": [""] * 5, "Cantidad": [1] * 5, "UM": ["EA"] * 5})
tabla = st.data_editor(
    vacia, key=f"tabla_{st.session_state.get('tabla_v', 0)}", num_rows="dynamic", use_container_width=True,
    hide_index=True,
    column_config={
        "Ítem": st.column_config.NumberColumn("Ítem", min_value=1, step=1, width="small",
                                              help="Se numera solo si lo deja vacío"),
        "OT": st.column_config.TextColumn("OT (9 dígitos)", default="", max_chars=9, width="small",
                                          validate=r"^\d{9}$", help="Orden de trabajo de 9 dígitos. Ej.: 201099001"),
        "N° de parte": st.column_config.TextColumn(default="", help="Tal como lo indica el fabricante"),
        "Descripción": st.column_config.TextColumn(default="", width="large", help="Ej.: PERNO HEXAGONAL"),
        "Marca NP": st.column_config.TextColumn("Marca NP", default="", width="small",
                                                help="Marca del número de parte (ESCO, BRADKEN...). Vacío = marca del equipo"),
        "Cantidad": st.column_config.NumberColumn(default=1, min_value=1, step=1, width="small"),
        "UM": st.column_config.SelectboxColumn("UM", options=UNIDADES, default="EA", width="small",
                                               help="Unidad de medida")})
t = tabla.copy()
for c in ("OT", "N° de parte", "Descripción", "Marca NP"):
    t[c] = t[c].fillna("").astype(str).str.strip().str.upper()
t["OT"] = t["OT"].str.replace(r"\.0$", "", regex=True)
t["Cantidad"] = pd.to_numeric(t["Cantidad"], errors="coerce").fillna(1)
t["UM"] = t["UM"].fillna("EA").replace("", "EA")
filas = t[(t["N° de parte"] != "") | (t["OT"] != "")].copy()
it = pd.to_numeric(filas["Ítem"], errors="coerce")
sig = int(it.max()) if it.notna().any() else 0
nums = []
for v in it:
    if pd.isna(v):
        sig += 1; nums.append(sig)
    else:
        nums.append(int(v))
filas["Ítem"] = nums
filas["Marca"] = [m or marca for m in filas["Marca NP"]]
ot_mal = filas[~filas["OT"].str.fullmatch(r"\d{9}")]
np_falta = filas[filas["N° de parte"] == ""]

if not filas.empty:
    filas["Texto para catalogar"] = [texto(d, n, m) for d, n, m in
                                     zip(filas["Descripción"], filas["N° de parte"], filas["Marca"])]
    filas["Largo"] = filas["Texto para catalogar"].str.len()
    cols_vista = ["Ítem", "OT", "N° de parte", "Descripción", "Marca", "Cantidad", "UM", "Texto para catalogar", "Largo"]
    if VERIFICA:
        filas["Verificación"] = [estado_np(n)[1] for n in filas["N° de parte"]]
        cols_vista.append("Verificación")
    st.markdown("**Vista previa**")
    st.dataframe(filas[cols_vista], hide_index=True, use_container_width=True,
                 column_config={"Cantidad": st.column_config.NumberColumn(format="%d"),
                                "Texto para catalogar": st.column_config.TextColumn(
                                    width="large", help="DESCRIPCIÓN,N° DE PARTE,MARCA (máx. 40 caracteres)"),
                                "Largo": st.column_config.ProgressColumn(min_value=0, max_value=40, format="%d")})
    n_ot = filas.loc[filas["OT"].str.fullmatch(r"\d{9}"), "OT"].nunique()
    st.caption(f"{len(filas)} NP en {n_ot} OT.")
    largos = filas[filas["Largo"] > 40]
    if not largos.empty:
        st.warning(f"{len(largos)} textos superan 40 caracteres: acorte la descripción "
                   f"({', '.join(largos['N° de parte'].head(5))}).")
    if not ot_mal.empty:
        st.error(f"{len(ot_mal)} filas con OT inválida: la OT debe tener 9 dígitos.")
    if not np_falta.empty:
        st.error(f"{len(np_falta)} filas con OT pero sin N° de parte.")
    if filas.duplicated(subset=["OT", "N° de parte"]).any():
        st.warning("Hay NP repetidos en la misma OT: se enviarán una sola vez con la cantidad sumada.")

# ---------------------------------------------------------------- 3. observaciones
paso(3, "Observaciones")
obs = st.text_area("Observaciones (opcional)", placeholder="Algún comentario sobre la solicitud...",
                   label_visibility="collapsed", height=90).strip()
adjuntos = st.file_uploader(f"Archivos adicionales (opcional): PDF, Excel, Word, imágenes, TXT... · máx. {MAX_MB} MB c/u",
                            accept_multiple_files=True, key=f"adj_{st.session_state.get('tabla_v', 0)}") or []
malos = [f.name for f in adjuntos if Path(f.name).suffix.lower() in BLOQUEADOS or f.size > MAX_MB * 1024 * 1024]
if malos:
    st.error("No se aceptan estos archivos (programas o más de " f"{MAX_MB} MB): " + ", ".join(malos))

errores = []
if not solicitante: errores.append("el solicitante")
if not equipo: errores.append("el equipo")
if filas.empty: errores.append("al menos un número de parte")
if not ot_mal.empty or not np_falta.empty: errores.append("corregir las filas marcadas en rojo")
if malos: errores.append("quitar los archivos no permitidos")
if errores:
    st.caption("Falta: " + ", ".join(errores) + ".")
if st.button("Enviar solicitud", type="primary", disabled=bool(errores), use_container_width=True):
    envio = (filas.groupby(["OT", "N° de parte"], as_index=False, sort=False)
             .agg({"Ítem": "first", "Descripción": "first", "Marca": "first", "Cantidad": "sum", "UM": "first"}))
    ahora = ahora_local()
    codigo = f"SOL-{ahora:%Y%m%d-%H%M%S}"
    nombres = [f.name for f in adjuntos]
    nota = obs + (" · " if obs and nombres else "") + (f"Adjuntos ({len(nombres)}): {', '.join(nombres)}" if nombres else "")
    salida = pd.DataFrame({
        "Código solicitud": codigo, "Fecha solicitud": ahora.strftime("%d/%m/%Y"), "Solicitante": solicitante,
        "Área": area, "Equipo": equipo, "Marca equipo": marca, "Flota": info.get("Flota", ""),
        "Clase de flota": info.get("Clase de flota", ""), "Modelo": info.get("Modelo", ""),
        "Nombre del equipo": info.get("Nombre del equipo", ""), "Ítem": envio["Ítem"].astype(int).values,
        "OT": envio["OT"].astype("int64").values, "NP solicitado": envio["N° de parte"].values,
        "Descripción": envio["Descripción"].values, "Vendor": envio["Marca"].values,
        "Cant.": envio["Cantidad"].astype(int).values, "UdM": envio["UM"].values,
        "Texto para catalogar": [texto(d, n, m) for d, n, m in zip(envio["Descripción"], envio["N° de parte"], envio["Marca"])],
        "Proyecto / Motivo": nota, "Adjuntos": ", ".join(nombres)})
    try:
        with st.spinner("Enviando..."):
            guardar(codigo, salida, adjuntos)
        ok = True
    except Exception as e:
        ok = False
        st.error(f"No se pudo enviar. Intente nuevamente en unos minutos. ({type(e).__name__}: {e})")
    if ok:
        st.session_state["enviado"] = (f"Solicitud **{codigo}** enviada: {len(salida)} NP en {salida['OT'].nunique()} OT"
                                       + (f" y {len(nombres)} archivo(s)" if nombres else "") + ". Gracias.")
        st.rerun()


st.caption("Planeamiento y Confiabilidad Mina · MMG Las Bambas · No incluya precios en este formulario.")
