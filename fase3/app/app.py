"""
Legajo Lakehouse · Fase 3 — Databricks App (Streamlit)
Dos vistas (POC):
  - 🏢 Portal del cliente: la persona jurídica sube la versión nueva de su documento.
       (En producción esto iría por el portal del banco vía API; acá se simula.)
  - ✅ Base Clientes: bandeja de aprobación. Al aprobar, promueve el binario y
       dispara el pipeline (AUTO CDC marca la versión anterior como reemplazada).
Estado transaccional en Lakebase; documentos/versiones en Delta/Unity Catalog.
"""
import os
import io
import re
import json
import uuid
import datetime
import contextlib

import streamlit as st
import psycopg
from databricks.sdk import WorkspaceClient

PIPELINE_ID = os.getenv("PIPELINE_ID", "")
VOL_STAGING = os.getenv("VOL_STAGING", "")
VOL_DOCS    = os.getenv("VOL_DOCS", "")
DB_INSTANCE = os.getenv("DATABRICKS_DATABASE_INSTANCE", "")

st.set_page_config(page_title="Legajo Lakehouse", page_icon="📂", layout="wide")
w = WorkspaceClient()


# --------------------------- infraestructura ---------------------------
def _pg_password() -> str:
    if os.getenv("PGPASSWORD"):
        return os.environ["PGPASSWORD"]
    try:
        return w.config.oauth_token().access_token
    except Exception:
        return w.database.generate_database_credential(
            request_id=str(uuid.uuid4()), instance_names=[DB_INSTANCE]).token


@contextlib.contextmanager
def get_conn():
    # PGUSER: explícito en env (local) o el usuario activo del workspace (app como SP)
    pguser = os.getenv("PGUSER") or w.current_user.me().user_name
    conn = psycopg.connect(
        host=os.getenv("PGHOST"), port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "databricks_postgres"),
        user=pguser, password=_pg_password(),
        sslmode=os.getenv("PGSSLMODE", "require"), autocommit=False)
    try:
        yield conn
    finally:
        conn.close()


def current_user() -> str:
    try:
        return w.current_user.me().user_name
    except Exception:
        return os.getenv("DATABRICKS_USER", "usuario")


def extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
        r = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in r.pages)
    except Exception:
        return ""


def chip(ok):
    return "🟢" if ok else "🔴"


# ============================ VISTA CLIENTE ============================
def fetch_notificadas():
    q = """
      SELECT id, cuit, razon_social, tipo_documento, fecha_venc_doc, estado
      FROM legajos.solicitudes
      WHERE estado IN ('notificado','pendiente_envio')
      ORDER BY fecha_venc_doc NULLS LAST, creado_en;
    """
    with get_conn() as c, c.cursor() as cur:
        cur.execute(q)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def registrar_subida(sol, data, usuario):
    """Sube el archivo a staging + valida preliminarmente + crea la subida."""
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    nombre = f"{sol['cuit']}_{sol['tipo_documento']}_v{ts}.pdf"
    staging_path = f"{VOL_STAGING}/{nombre}"
    w.files.upload(staging_path, io.BytesIO(data), overwrite=True)

    texto = extract_pdf_text(data)
    solo_digitos = re.sub(r"\D", "", texto)
    anios = [int(a) for a in re.findall(r"\b(20\d{2})\b", texto)]
    validaciones = {
        "cuit_coincide": sol["cuit"] in solo_digitos,
        "tipo_coincide": sol["tipo_documento"].split("_")[0].lower() in texto.lower(),
        "fecha_posterior": bool(anios) and max(anios) >= datetime.date.today().year,
    }
    with get_conn() as c, c.cursor() as cur:
        cur.execute(
            "INSERT INTO legajos.subidas (solicitud_id, nombre_archivo, ruta_staging, "
            "validaciones, resumen_nuevo, subido_por) VALUES (%s,%s,%s,%s,%s,%s)",
            (sol["id"], nombre, staging_path, json.dumps(validaciones), texto[:280], usuario))
        cur.execute(
            "UPDATE legajos.solicitudes SET estado='pendiente_aprobacion', actualizado_en=now() WHERE id=%s",
            (sol["id"],))
        c.commit()
    return validaciones


def vista_cliente(usuario):
    st.title("🏢 Portal del cliente · renovación documental")
    st.caption("Simulación del portal de autogestión. En producción, la subida entra por el "
               "portal del banco vía API; el circuito posterior es idéntico.")

    # Mostrar resultado de la subida anterior (persiste a través del rerun)
    if "subida_ok" in st.session_state:
        info = st.session_state.pop("subida_ok")
        v = info["validaciones"]
        st.success(f"✅ Documento recibido. **{info['razon_social']} — {info['tipo']}** "
                   "quedó pendiente de aprobación por Base Clientes.")
        st.markdown(f"- {chip(v['cuit_coincide'])} el CUIT del documento coincide  \n"
                    f"- {chip(v['tipo_coincide'])} el tipo coincide con el pedido  \n"
                    f"- {chip(v['fecha_posterior'])} la fecha parece posterior")

    pend = fetch_notificadas()
    if not pend:
        st.info("No tenés documentos pendientes de renovación en este momento.")
        return
    labels = {f"{s['razon_social']} — {s['tipo_documento']} (vence {s['fecha_venc_doc']})": s for s in pend}
    sel = st.selectbox("Documento a renovar", list(labels.keys()))
    sol = labels[sel]
    st.markdown(f"Subí la versión nueva del **{sol['tipo_documento']}** de **{sol['razon_social']}** (CUIT `{sol['cuit']}`).")
    archivo = st.file_uploader("Archivo PDF", type=["pdf"])
    if archivo and st.button("📤 Enviar para aprobación", type="primary"):
        with st.spinner("Subiendo a staging y validando..."):
            v = registrar_subida(sol, archivo.getvalue(), usuario)
        st.session_state["subida_ok"] = {
            "razon_social": sol["razon_social"],
            "tipo": sol["tipo_documento"],
            "validaciones": v,
        }
        st.rerun()


# ============================ VISTA APROBACIÓN ============================
def fetch_pendientes():
    q = """
      SELECT s.id, s.cuit, s.razon_social, s.tipo_documento, s.fecha_venc_doc,
             s.resumen_anterior, s.id_version_anterior,
             u.id AS subida_id, u.nombre_archivo, u.ruta_staging, u.file_hash,
             u.validaciones, u.resumen_nuevo, u.subido_por, u.subido_en
      FROM legajos.solicitudes s
      JOIN LATERAL (SELECT * FROM legajos.subidas su WHERE su.solicitud_id = s.id
                    ORDER BY su.subido_en DESC LIMIT 1) u ON true
      WHERE s.estado = 'pendiente_aprobacion'
      ORDER BY s.fecha_venc_doc NULLS LAST, s.creado_en;
    """
    with get_conn() as c, c.cursor() as cur:
        cur.execute(q)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def aprobar(sol, usuario):
    destino = f"{VOL_DOCS}/{sol['nombre_archivo']}"
    data = w.files.download(sol["ruta_staging"]).contents.read()
    w.files.upload(destino, io.BytesIO(data), overwrite=True)
    with get_conn() as c, c.cursor() as cur:
        cur.execute("INSERT INTO legajos.aprobaciones (solicitud_id, subida_id, decision, aprobado_por) "
                    "VALUES (%s,%s,'aprobado',%s)", (sol["id"], sol["subida_id"], usuario))
        cur.execute("UPDATE legajos.solicitudes SET estado='aprobado', actualizado_en=now() WHERE id=%s",
                    (sol["id"],))
        c.commit()
    w.pipelines.start_update(pipeline_id=PIPELINE_ID)


def rechazar(sol, usuario, motivo):
    with get_conn() as c, c.cursor() as cur:
        cur.execute("INSERT INTO legajos.aprobaciones (solicitud_id, subida_id, decision, motivo, aprobado_por) "
                    "VALUES (%s,%s,'rechazado',%s,%s)", (sol["id"], sol["subida_id"], motivo, usuario))
        cur.execute("UPDATE legajos.solicitudes SET estado='rechazado', actualizado_en=now() WHERE id=%s",
                    (sol["id"],))
        c.commit()


def vista_aprobacion(usuario):
    st.title("✅ Bandeja de aprobación · Base Clientes")
    st.caption("Aprobación de versiones documentales")

    # Mostrar resultado de la acción anterior (persiste a través del rerun)
    if "decision_ok" in st.session_state:
        info = st.session_state.pop("decision_ok")
        if info["decision"] == "aprobado":
            st.success(f"✅ **{info['razon_social']} — {info['tipo']}** aprobado. "
                       "La versión nueva entra al pipeline; la anterior pasará a reemplazada.")
        else:
            st.warning(f"❌ **{info['razon_social']} — {info['tipo']}** rechazado. "
                       "Se notificará al cliente y sigue el ciclo de alertas.")

    pend = fetch_pendientes()
    st.markdown(f"### {len(pend)} solicitud(es) pendiente(s)")
    for sol in pend:
        v = sol["validaciones"] or {}
        if isinstance(v, str):
            v = json.loads(v)
        with st.container(border=True):
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown(f"#### {sol['razon_social']} — *{sol['tipo_documento']}*")
                st.markdown(f"CUIT `{sol['cuit']}` · vence **{sol['fecha_venc_doc']}**")
                st.markdown(f"**Archivo:** `{sol['nombre_archivo']}` · por {sol['subido_por']}")
                st.markdown(f"- {chip(v.get('tipo_coincide'))} el tipo coincide  \n"
                            f"- {chip(v.get('cuit_coincide'))} el CUIT coincide  \n"
                            f"- {chip(v.get('fecha_posterior'))} la fecha es posterior")
            with c2:
                st.markdown("**Versión anterior (vigente hoy)**")
                st.caption((sol["resumen_anterior"] or "—")[:300])
                st.markdown("**Versión nueva (a aprobar)**")
                st.caption((sol["resumen_nuevo"] or "—")[:300])
            b1, b2, _ = st.columns([1, 1, 3])
            if b1.button("✅ Aprobar", key=f"ap_{sol['id']}", type="primary"):
                with st.spinner("Promoviendo binario y disparando reproceso..."):
                    aprobar(sol, usuario)
                st.session_state["decision_ok"] = {
                    "decision": "aprobado",
                    "razon_social": sol["razon_social"],
                    "tipo": sol["tipo_documento"],
                }
                st.rerun()
            with b2.popover("❌ Rechazar"):
                motivo = st.text_input("Motivo", key=f"mot_{sol['id']}")
                if st.button("Confirmar rechazo", key=f"rj_{sol['id']}"):
                    rechazar(sol, usuario, motivo or "sin motivo")
                    st.session_state["decision_ok"] = {
                        "decision": "rechazado",
                        "razon_social": sol["razon_social"],
                        "tipo": sol["tipo_documento"],
                    }
                    st.rerun()
                    st.rerun()
    if not pend:
        st.info("No hay solicitudes pendientes de aprobación.")


# ------------------------------- router -------------------------------
usuario = current_user()
st.sidebar.markdown(f"**Usuario:** {usuario}")
vista = st.sidebar.radio("Vista", ["🏢 Portal del cliente", "✅ Base Clientes (aprobación)"])
if st.sidebar.button("🔄 Refrescar"):
    st.rerun()

try:
    if vista.startswith("🏢"):
        vista_cliente(usuario)
    else:
        vista_aprobacion(usuario)
except Exception as e:
    st.error(f"Error: {e}")
