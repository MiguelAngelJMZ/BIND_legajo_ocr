-- =============================================================================
-- SILVER · Resolución de entidad + GATE  (todo STREAMING TABLES)
-- Streaming tables -> CDF real (a diferencia de las MV). Resolución por fila
-- (filename / contenido) + stream-static join al maestro; sin GROUP BY.
-- =============================================================================

-- Texto plano por documento (streaming, append).
CREATE OR REFRESH STREAMING TABLE documentos_texto
COMMENT 'Texto concatenado de los elementos parseados.'
AS
SELECT
  file_name, file_path, file_size, file_hash, file_modification_time, parsed_content,
  concat_ws('\n\n',
    transform(
      try_cast(parsed_content:document:elements AS ARRAY<VARIANT>),
      e -> try_cast(e:content AS STRING)
    )
  ) AS texto_completo,
  try_cast(parsed_content:error_status AS STRING) AS error_status
FROM STREAM(documentos_bronze);

-- Candidatos de CUIT por fila: nivel 1 (filename) y nivel 3 (contenido).
-- (El nivel 2 por razón social — que requería scan-join agregado — se difiere;
--  en el POC todo resuelve por filename o contenido.)
CREATE OR REFRESH STREAMING TABLE documentos_resueltos
COMMENT 'CUIT candidato y método de resolución, por fila.'
AS
SELECT
  file_name, file_path, file_size, file_hash, file_modification_time,
  parsed_content, texto_completo,
  coalesce(cuit_filename, cuit_contenido)  AS cuit_resuelto,
  CASE
    WHEN cuit_filename  IS NOT NULL THEN 'deterministico_filename'
    WHEN cuit_contenido IS NOT NULL THEN 'contenido'
    ELSE 'sin_resolver'
  END AS metodo_resolucion
FROM (
  SELECT
    file_name, file_path, file_size, file_hash, file_modification_time,
    parsed_content, texto_completo,
    nullif(regexp_extract(file_name, '([0-9]{11})', 1), '')                       AS cuit_filename,
    nullif(regexp_extract(regexp_replace(texto_completo, '[-\\.\\s]', ''),
                          '([0-9]{11})', 1), '')                                   AS cuit_contenido
  FROM STREAM(documentos_texto)
  WHERE error_status IS NULL
);

-- GATE: stream-static JOIN al maestro. Solo lo validado avanza.
CREATE OR REFRESH STREAMING TABLE documentos_con_dueno
COMMENT 'Documentos que pasaron el gate: CUIT validado contra el maestro.'
AS
SELECT
  r.file_name, r.file_path, r.file_size, r.file_hash, r.file_modification_time,
  r.parsed_content, r.texto_completo,
  r.cuit_resuelto AS cuit,
  pj.razon_social, pj.oficial_cuenta, pj.email_contacto,
  r.metodo_resolucion
FROM STREAM(documentos_resueltos) r
JOIN personas_juridicas pj
  ON r.cuit_resuelto = pj.cuit;

-- COLA DE REVISIÓN: stream-static LEFT JOIN, lo que no matchea el maestro.
CREATE OR REFRESH STREAMING TABLE cola_revision
COMMENT 'Documentos sin dueño resoluble.'
AS
SELECT
  r.file_name, r.file_path, r.metodo_resolucion, r.cuit_resuelto,
  CASE WHEN r.cuit_resuelto IS NULL THEN 'no_se_detecto_cuit'
       ELSE 'cuit_no_esta_en_maestro' END AS motivo_revision,
  left(r.texto_completo, 500) AS extracto
FROM STREAM(documentos_resueltos) r
LEFT JOIN personas_juridicas pj
  ON r.cuit_resuelto = pj.cuit
WHERE pj.cuit IS NULL;
