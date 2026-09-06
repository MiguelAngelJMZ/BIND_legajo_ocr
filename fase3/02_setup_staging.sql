-- =============================================================================
-- Fase 3 · Volume de STAGING (Unity Catalog)
-- Zona separada del repositorio aprobado. El cliente sube acá; al aprobar,
-- el binario se promueve a /Volumes/{catalog}/{schema}/documentacion/ (ingesta).
-- Ejecutar con run_sql.py --catalog <cat> --schema <schema>:
--   python3 run_sql.py fase3/02_setup_staging.sql \
--     --profile <perfil> --warehouse <id> --catalog <cat> --schema <schema>
-- =============================================================================
CREATE VOLUME IF NOT EXISTS {catalog}.{schema}.staging;
