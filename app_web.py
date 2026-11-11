"""
FORMULARIO WEB DE SOLICITUD DE CATALOGACIÓN (versión publicada en Streamlit Community Cloud)

- No lee la base de MMG (no se sube a internet): solo recibe solicitudes.
- Cada envío se agrega a una hoja de Google Sheets (pestaña "Solicitudes").
- En la PC de Planeamiento, ACTUALIZAR_BASE.bat descarga las filas nuevas y las pasa a la base.
- Credenciales y código de acceso en Settings > Secrets (nunca en el repositorio).
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
EQUIPOS = ["SH001", "SH002", "SH003", "SH004", "SH005", "SH011", "SH012", "SH013", "EX020", "6060", "6060FS", "7495",
           "TD002", "TD003", "TD004", "TD005", "TD006", "TD007", "TD008", "TD009", "TD010", "TD013", "TD014",
           "MD6640", "P&H 320XPC", "LD001", "LT2350"]
MARCAS = {"KOMATSU": "KOMATSU", "P&H": "P&H", "CAT": "CAT", "EPIROC": "EPIROC", "MTU": "MTU", "OTROS": ""}
HOJA = "Solicitudes"
COLUMNAS = ["Código solicitud", "Fecha solicitud", "Solicitante", "Área", "Equipo", "Vendor", "OT", "NP solicitado",
            "Descripción", "Cant.", "Texto para catalogar", "Proyecto / Motivo"]
ZONA = ZoneInfo("America/Lima")

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
</style>""", unsafe_allow_html=True)
logo = f'<img src="data:image/png;base64,{base64.b64encode(LOGO.read_bytes()).decode()}">' if LOGO.exists() else ""
st.markdown(f"""<div class="cab">{logo}<div><h1>Solicitud de catalogación de materiales</h1>
<p>Superintendencia de Mantenimiento Mina · Planeamiento y Confiabilidad Mina</p></div></div>
<div class="franja">{"".join(f'<div style="background:{c}"></div>' for c in (ROJO, NARANJA, AZUL, VERDE, "#006838"))}</div>""",
            unsafe_allow_html=True)


def paso(n, txt):
    st.markdown(f'<div class="paso"><span>{n}</span><b>{txt}</b></div>', unsafe_allow_html=True)


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
def hoja():
    import gspread
    gc = gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
    libro = gc.open_by_url(st.secrets["hoja_url"])
    try:
        ws = libro.worksheet(HOJA)
    except gspread.WorksheetNotFound:
        ws = libro.add_worksheet(HOJA, rows=1000, cols=len(COLUMNAS))
    if ws.row_values(1) != COLUMNAS:
        ws.update([COLUMNAS], "A1")
    return ws


def texto(desc, np_, marca):
    return ",".join(x for x in (desc, np_, marca) if x)


# ================================================================== formulario
if st.session_state.get("enviado"):
    st.success(st.session_state["enviado"])
    if st.button("Registrar otra solicitud"):
        st.session_state.pop("enviado"); st.session_state["tabla_v"] = st.session_state.get("tabla_v", 0) + 1
        st.rerun()
    st.stop()

paso(1, "Datos")
c1, c2 = st.columns([2, 1])
solicitante = c1.text_input("Solicitante *", placeholder="NOMBRES Y APELLIDOS", help="Se guarda en mayúsculas.").strip().upper()
area = c2.selectbox("Área *", AREAS)
c3, c4, c5 = st.columns(3)
equipo = c3.selectbox("Equipo *", EQUIPOS + ["Otro"])
if equipo == "Otro":
    equipo = c3.text_input("Indique el equipo").strip().upper()
marca_op = c4.selectbox("Marca *", list(MARCAS))
marca = MARCAS[marca_op]
if marca_op == "OTROS":
    marca = c5.text_input("Indique la marca *", placeholder="Ej.: SANDVIK").strip().upper()

paso(2, "Números de parte")
st.caption("Una fila por N° de parte. Una OT puede tener muchos NP: repita la OT en cada fila. "
           "Puede copiar y pegar desde Excel (OT · N° de parte · Descripción · Cantidad). "
           "Use el ➕ o escriba en la última fila para agregar más.")
vacia = pd.DataFrame({"OT": [""] * 5, "N° de parte": [""] * 5, "Descripción": [""] * 5, "Cantidad": [1] * 5})
tabla = st.data_editor(
    vacia, key=f"tabla_{st.session_state.get('tabla_v', 0)}", num_rows="dynamic", use_container_width=True, hide_index=True,
    column_config={
        "OT": st.column_config.TextColumn("OT (9 dígitos)", default="", max_chars=9, width="small", validate=r"^\d{9}$",
                                          help="Orden de trabajo de 9 dígitos. Ej.: 201099001"),
        "N° de parte": st.column_config.TextColumn(default="", help="Tal como lo indica el fabricante"),
        "Descripción": st.column_config.TextColumn(default="", width="large", help="Ej.: PERNO HEXAGONAL"),
        "Cantidad": st.column_config.NumberColumn(default=1, min_value=1, step=1, width="small")})
t = tabla.copy()
for c in ("OT", "N° de parte", "Descripción"):
    t[c] = t[c].fillna("").astype(str).str.strip().str.upper()
t["OT"] = t["OT"].str.replace(r"\.0$", "", regex=True)
t["Cantidad"] = pd.to_numeric(t["Cantidad"], errors="coerce").fillna(1)
filas = t[(t["N° de parte"] != "") | (t["OT"] != "")].copy()
ot_mal = filas[~filas["OT"].str.fullmatch(r"\d{9}")]
np_falta = filas[filas["N° de parte"] == ""]

if not filas.empty:
    filas["Texto para catalogar"] = [texto(d, n, marca) for d, n in zip(filas["Descripción"], filas["N° de parte"])]
    filas["Largo"] = filas["Texto para catalogar"].str.len()
    st.markdown("**Vista previa**")
    st.dataframe(filas[["OT", "N° de parte", "Descripción", "Cantidad", "Texto para catalogar", "Largo"]],
                 hide_index=True, use_container_width=True,
                 column_config={"Cantidad": st.column_config.NumberColumn(format="%d"),
                                "Texto para catalogar": st.column_config.TextColumn(
                                    width="large", help="DESCRIPCIÓN,N° DE PARTE,MARCA (máx. 40 caracteres)"),
                                "Largo": st.column_config.ProgressColumn(min_value=0, max_value=40, format="%d")})
    n_ot = filas.loc[filas["OT"].str.fullmatch(r"\d{9}"), "OT"].nunique()
    st.caption(f"{len(filas)} NP en {n_ot} OT.")
    largos = filas[filas["Largo"] > 40]
    if not largos.empty:
        st.warning(f"{len(largos)} textos superan 40 caracteres: acorte la descripción ({', '.join(largos['N° de parte'].head(5))}).")
    if not ot_mal.empty:
        st.error(f"{len(ot_mal)} filas con OT inválida: la OT debe tener 9 dígitos.")
    if not np_falta.empty:
        st.error(f"{len(np_falta)} filas con OT pero sin N° de parte.")
    if filas.duplicated(subset=["OT", "N° de parte"]).any():
        st.warning("Hay NP repetidos en la misma OT: se enviarán una sola vez con la cantidad sumada.")

paso(3, "Observaciones")
obs = st.text_area("Observaciones (opcional)", placeholder="Algún comentario sobre la solicitud...",
                   label_visibility="collapsed", height=90).strip()

errores = []
if not solicitante: errores.append("el solicitante")
if not equipo: errores.append("el equipo")
if not marca: errores.append("la marca")
if filas.empty: errores.append("al menos un número de parte")
if not ot_mal.empty or not np_falta.empty: errores.append("corregir las filas marcadas en rojo")
if errores:
    st.caption("Falta: " + ", ".join(errores) + ".")
if st.button("Enviar solicitud", type="primary", disabled=bool(errores), use_container_width=True):
    envio = filas.groupby(["OT", "N° de parte"], as_index=False, sort=False).agg({"Descripción": "first", "Cantidad": "sum"})
    ahora = datetime.now(ZONA)
    codigo = f"SOL-{ahora:%Y%m%d-%H%M%S}"
    nuevas = [[codigo, ahora.strftime("%d/%m/%Y"), solicitante, area, equipo, marca, int(r["OT"]), r["N° de parte"],
               r["Descripción"], int(r["Cantidad"]), texto(r["Descripción"], r["N° de parte"], marca), obs]
              for _, r in envio.iterrows()]
    try:
        with st.spinner("Enviando..."):
            hoja().append_rows(nuevas, value_input_option="RAW")
        st.session_state["enviado"] = (f"Solicitud **{codigo}** enviada: {len(nuevas)} NP en {envio['OT'].nunique()} OT. "
                                       "Gracias, Planeamiento y Confiabilidad Mina la registrará.")
        st.rerun()
    except Exception as e:
        st.error(f"No se pudo enviar. Intente nuevamente en unos minutos. ({type(e).__name__})")

st.caption("Planeamiento y Confiabilidad Mina · MMG Las Bambas · No incluya precios en este formulario.")
