#!/usr/bin/env python3
"""
Seed de la bandeja de aprobación (Fase 3, demo).
1) Lee documentos VENCIDOS de <catalog>.<schema>.versiones (vía warehouse).
2) Para un subconjunto, genera un PDF "renovado" (misma entidad+tipo, venc. futuro),
   lo sube al Volume de STAGING y computa validaciones preliminares.
3) Inserta la solicitud (pendiente_aprobacion) + la subida en Lakebase.

Uso:
  python3 seed_solicitudes.py \
    --profile <perfil> --warehouse <id> \
    --catalog <catalogo> --schema <schema> \
    --pghost <lakebase_host> --pguser <email> \
    --estado notificado
"""
import os, argparse, uuid, json, tempfile, datetime
import psycopg
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

ap = argparse.ArgumentParser()
ap.add_argument("--profile",    required=True, help="Perfil CLI de Databricks")
ap.add_argument("--warehouse",  required=True, help="ID del SQL warehouse serverless")
ap.add_argument("--catalog",    required=True, help="Catálogo Unity Catalog")
ap.add_argument("--schema",     required=True, help="Schema destino")
ap.add_argument("--limit",      type=int, default=2)
ap.add_argument("--estado",     default="pendiente_aprobacion",
                help="pendiente_aprobacion (sube a staging) | notificado (solo crea la solicitud)")
ap.add_argument("--pghost",     default=os.getenv("PGHOST"),     required=True)
ap.add_argument("--pgport",     default=os.getenv("PGPORT", "5432"))
ap.add_argument("--pgdb",       default=os.getenv("PGDATABASE", "databricks_postgres"))
ap.add_argument("--pguser",     default=os.getenv("PGUSER"),     required=True)
ap.add_argument("--pgpassword", default=os.getenv("PGPASSWORD"))
args = ap.parse_args()

VOL_STAGING = f"/Volumes/{args.catalog}/{args.schema}/staging"
w = WorkspaceClient(profile=args.profile)

# Password = token OAuth U2M si no se pasó explícitamente (igual que run_pg.py)
if not args.pgpassword:
    args.pgpassword = w.config.oauth_token().access_token


def sql(stmt):
    r = w.statement_execution.execute_statement(
        warehouse_id=args.warehouse, statement=stmt, wait_timeout="50s")
    if r.status.state != StatementState.SUCCEEDED:
        raise RuntimeError(r.status.error.message if r.status.error else r.status.state)
    return r.result.data_array or []


def gen_pdf_renovado(razon_social, tipo, cuit, venc_futuro):
    styles = getSampleStyleSheet()
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=2*cm)
    story = [
        Paragraph(f"{tipo.upper().replace('_',' ')} — RENOVACION", styles["Title"]),
        Paragraph(razon_social, styles["Heading2"]),
        Spacer(1, 12),
        Paragraph(f"Razon social: {razon_social}", styles["BodyText"]),
        Paragraph(f"CUIT: {cuit}", styles["BodyText"]),
        Paragraph(f"Fecha de emision: {datetime.date.today().strftime('%d/%m/%Y')}", styles["BodyText"]),
        Paragraph(f"Vigencia hasta: {venc_futuro}", styles["BodyText"]),
        Spacer(1, 12),
        Paragraph("Version renovada del documento, presentada por el cliente para su aprobacion "
                  "por el area Base Clientes. Reemplaza a la version anterior vencida.", styles["BodyText"]),
    ]
    doc.build(story)
    return path


# 1) vencidos (versión vigente actual = __END_AT IS NULL en el SCD2 de versiones)
rows = sql("""
  SELECT cuit, razon_social, tipo_documento,
         CAST(fecha_vencimiento AS STRING),
         id_version, substr(texto_completo,1,280)
  FROM {catalog}.{schema}.versiones
  WHERE estado='vencido' AND `__END_AT` IS NULL
  ORDER BY fecha_vencimiento
  LIMIT {limit}
""".format(catalog=args.catalog, schema=args.schema, limit=args.limit))
print(f"Vencidos a sembrar: {len(rows)}")

conn = psycopg.connect(host=args.pghost, port=int(args.pgport), dbname=args.pgdb,
                       user=args.pguser, password=args.pgpassword,
                       sslmode=os.getenv("PGSSLMODE", "require"), autocommit=True)

for cuit, razon, tipo, venc, id_ver, resumen_ant in rows:
    # evitar duplicar: saltar si ya hay una solicitud abierta para (cuit, tipo)
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM legajos.solicitudes WHERE cuit=%s AND tipo_documento=%s "
                    "AND estado NOT IN ('aprobado','rechazado') LIMIT 1", (cuit, tipo))
        if cur.fetchone():
            print(f"  – {razon} / {tipo}: ya tiene solicitud abierta, se omite")
            continue

    if args.estado == "notificado":
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO legajos.solicitudes
                  (cuit, razon_social, tipo_documento, motivo, estado, fecha_venc_doc,
                   id_version_anterior, resumen_anterior)
                VALUES (%s,%s,%s,'vencimiento','notificado',%s,%s,%s)
            """, (cuit, razon, tipo, venc, id_ver, resumen_ant))
        print(f"  ✓ solicitud {razon} / {tipo} -> notificado (esperando subida del cliente)")
        continue

    # modo pendiente_aprobacion: simula que el cliente ya subió (staging + subida)
    venc_futuro = "31/12/2030"
    nombre = f"{cuit}_{tipo}_renovacion.pdf"
    local = gen_pdf_renovado(razon, tipo, cuit, venc_futuro)
    staging_path = f"{VOL_STAGING}/{nombre}"
    with open(local, "rb") as f:
        w.files.upload(staging_path, f, overwrite=True)
    validaciones = {"tipo_coincide": True, "cuit_coincide": True, "fecha_posterior": True}
    resumen_nuevo = f"Version renovada de {tipo} de {razon}. Vigencia hasta {venc_futuro}."
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO legajos.solicitudes
              (cuit, razon_social, tipo_documento, motivo, estado, fecha_venc_doc,
               id_version_anterior, resumen_anterior)
            VALUES (%s,%s,%s,'vencimiento','pendiente_aprobacion',%s,%s,%s)
            RETURNING id
        """, (cuit, razon, tipo, venc, id_ver, resumen_ant))
        sid = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO legajos.subidas
              (solicitud_id, nombre_archivo, ruta_staging, validaciones, resumen_nuevo, subido_por)
            VALUES (%s,%s,%s,%s,%s,'cliente_demo')
        """, (sid, nombre, staging_path, json.dumps(validaciones), resumen_nuevo))
    print(f"  ✓ solicitud {razon} / {tipo} -> pendiente_aprobacion (staging: {nombre})")

conn.close()
print("Seed completo.")
