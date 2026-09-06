-- =============================================================================
-- SILVER/GOLD · Extracción + normalización + VERSIONES (AUTO CDC / APPLY CHANGES)
-- El versionado del diseño se resuelve con APPLY CHANGES SCD TYPE 2:
-- clave = (cuit, tipo_documento), secuencia = file_modification_time.
-- v.N+1 pasa a vigente y v.N a histórico (__END_AT) automáticamente.
-- =============================================================================

-- Extracción con funciones AI (streaming, por fila -> costo incremental).
CREATE OR REFRESH STREAMING TABLE documentos_extraidos
COMMENT 'Tipo de documento y fechas extraídas.'
AS
SELECT
  d.*,
  ai_classify(d.texto_completo, ARRAY(
    'estatuto','poder','acta_designacion_autoridades','documento_identidad',
    'controles_internos','consultas_web','estados_contables',
    'constancia_inscripcion','informe_crediticio','otro')) AS tipo_documento,
  ai_extract(d.texto_completo, ARRAY('fecha_emision','fecha_vencimiento')) AS fechas_raw
FROM STREAM(documentos_con_dueno) d;

-- Normalización: fechas a DATE, regla de vencimiento por tipo, estado, id_version.
CREATE OR REFRESH STREAMING TABLE documentos_norm
COMMENT 'Registro normalizado por documento/versión. Fuente del AUTO CDC.'
AS
WITH b AS (
  SELECT
    file_name, file_path, file_hash, file_modification_time,
    cuit, razon_social, oficial_cuenta, email_contacto, metodo_resolucion,
    texto_completo, tipo_documento,
    try_to_date(nullif(fechas_raw.fecha_emision, ''),     'd/M/y') AS fecha_emision,
    try_to_date(nullif(fechas_raw.fecha_vencimiento, ''), 'd/M/y') AS fecha_venc_explicita
  FROM STREAM(documentos_extraidos)
)
SELECT
  file_name, file_path, file_hash, file_modification_time,
  cuit, razon_social, oficial_cuenta, email_contacto, metodo_resolucion,
  tipo_documento, texto_completo, fecha_emision,
  coalesce(
    fecha_venc_explicita,
    CASE tipo_documento
      WHEN 'estados_contables'      THEN add_months(fecha_emision, 12)
      WHEN 'constancia_inscripcion' THEN date_add(fecha_emision, 180)
      ELSE NULL END
  ) AS fecha_vencimiento,
  concat(file_hash, '_v', date_format(file_modification_time, 'yyyyMMddHHmmss')) AS id_version,
  CASE
    WHEN coalesce(fecha_venc_explicita,
           CASE tipo_documento
             WHEN 'estados_contables'      THEN add_months(fecha_emision, 12)
             WHEN 'constancia_inscripcion' THEN date_add(fecha_emision, 180)
             ELSE NULL END) IS NULL                                   THEN 'vigente'
    WHEN coalesce(fecha_venc_explicita,
           CASE tipo_documento
             WHEN 'estados_contables'      THEN add_months(fecha_emision, 12)
             WHEN 'constancia_inscripcion' THEN date_add(fecha_emision, 180)
             ELSE NULL END) <  current_date()                         THEN 'vencido'
    WHEN coalesce(fecha_venc_explicita,
           CASE tipo_documento
             WHEN 'estados_contables'      THEN add_months(fecha_emision, 12)
             WHEN 'constancia_inscripcion' THEN date_add(fecha_emision, 180)
             ELSE NULL END) <= date_add(current_date(), 60)           THEN 'por_vencer'
    ELSE 'vigente'
  END AS estado
FROM b;

-- VERSIONES · AUTO CDC (SCD TYPE 2). Histórico auditable + versión vigente.
CREATE OR REFRESH STREAMING TABLE versiones
COMMENT 'GOLD · Versión por (cuit, tipo_documento) con historial SCD2. Alimenta Genie/inventario.';

APPLY CHANGES INTO versiones
FROM STREAM(documentos_norm)
KEYS (cuit, tipo_documento)
SEQUENCE BY file_modification_time
STORED AS SCD TYPE 2;
