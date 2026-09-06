-- =============================================================================
-- Legajo Lakehouse · Setup inicial (one-time)
-- Crea catálogo, schema, volumen y el MAESTRO de personas jurídicas.
-- Ejecutar vía run_sql.py pasando --catalog y --schema:
--   python3 run_sql.py src/setup/01_setup_catalogo.sql \
--     --profile <perfil> --warehouse <id> \
--     --catalog <catalogo> --schema <schema>
--
-- MANAGED LOCATION: en algunos sandboxes el catálogo requiere una external
-- location explícita. Si CREATE CATALOG falla con un error de ubicación,
-- descomentar la línea MANAGED LOCATION y ajustar la ruta S3/ABFS del entorno.
-- =============================================================================

CREATE CATALOG IF NOT EXISTS {catalog};
-- MANAGED LOCATION 's3://<bucket>/{catalog}';   -- descomentar si el workspace lo requiere
CREATE SCHEMA  IF NOT EXISTS {catalog}.{schema};

-- Volumen donde "llegan" los binarios (asumimos ingesta ya resuelta).
CREATE VOLUME IF NOT EXISTS {catalog}.{schema}.documentacion;

-- -----------------------------------------------------------------------------
-- Maestro de personas jurídicas.
-- Reemplaza el CASE WHEN hardcodeado del notebook original.
-- Es una tabla de referencia: la LEE el pipeline, no la produce.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS {catalog}.{schema}.personas_juridicas (
  cuit            STRING  COMMENT 'CUIT sin guiones (11 dígitos), clave del maestro',
  razon_social    STRING,
  razon_social_norm STRING COMMENT 'Razón social normalizada para match por reglas',
  oficial_cuenta  STRING,
  email_contacto  STRING
)
COMMENT 'Maestro de entidades. Semilla desde Complif en el diseño real.'
TBLPROPERTIES (delta.enableChangeDataFeed = true);

-- Semilla (las 4 entidades ficticias del POC).
INSERT INTO {catalog}.{schema}.personas_juridicas VALUES
  ('30712345678','Estancias del Sur S.A.',     'estancias del sur sa',    'Ana Gómez',    'legales@estanciasdelsur.example'),
  ('30709876543','Logística Andina S.R.L.',    'logistica andina srl',    'Pablo Ruiz',   'admin@logandina.example'),
  ('33698765439','Grupo Textil Paraná S.A.',   'grupo textil parana sa',  'Ana Gómez',    'finanzas@textilparana.example'),
  ('30715558882','Consultora Rivadavia S.A.S.','consultora rivadavia sas','Pablo Ruiz',   'contacto@rivadavia.example');
