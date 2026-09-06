-- =============================================================================
-- GOLD · chunks  (AUTO CDC / APPLY CHANGES SCD TYPE 1)
-- Fuente del índice Vector Search. Clave = chunk_key (cuit|tipo|idx).
-- Una versión nueva hace UPSERT de sus chunks y, vía APPLY AS DELETE, RETIRA los
-- slots huérfanos que la versión anterior ocupaba (chunks que encogen).
-- CDF real → Vector Search sincroniza solo el delta.
-- =============================================================================
CREATE OR REFRESH STREAMING TABLE chunks
COMMENT 'GOLD · Chunks de la versión vigente por documento. Fuente del índice vectorial.'
TBLPROPERTIES (delta.enableChangeDataFeed = true);

APPLY CHANGES INTO chunks
FROM STREAM(chunks_stream)
KEYS (chunk_key)
APPLY AS DELETE WHEN _op = 'delete'
SEQUENCE BY file_modification_time
COLUMNS * EXCEPT (_op)
STORED AS SCD TYPE 1;
