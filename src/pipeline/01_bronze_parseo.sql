-- =============================================================================
-- BRONZE · Parseo incremental
-- ai_parse_document sobre los binarios del Volume. Streaming table: procesa
-- SOLO archivos nuevos (checkpoint) -> no re-paga el parseo del stock ya visto.
-- Corrige el CREATE OR REPLACE del notebook original.
-- =============================================================================

CREATE OR REFRESH STREAMING TABLE documentos_bronze
COMMENT 'Binarios parseados con OCR. Un registro por archivo del Volume.'
AS
SELECT
  _metadata.file_name                       AS file_name,
  _metadata.file_path                       AS file_path,
  _metadata.file_size                       AS file_size,
  _metadata.file_modification_time          AS file_modification_time,
  -- hash para deduplicar entre fuentes (bloque #3 del plan)
  sha2(content, 256)                        AS file_hash,
  ai_parse_document(
    content,
    map('version', '2.0', 'descriptionElementTypes', '*')
  )                                         AS parsed_content
FROM STREAM read_files(
  '${docs_volume_path}',   -- ruta del Volume, inyectada desde databricks.yml (configuration)
  format => 'binaryFile'
);
