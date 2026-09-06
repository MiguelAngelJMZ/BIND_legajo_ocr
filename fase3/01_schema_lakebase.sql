-- =============================================================================
-- Fase 3 · Esquema Lakebase (Postgres OLTP) — estado transaccional del workflow
-- Ejecutar contra el branch production de la instancia Lakebase del entorno.
-- Guarda SOLO el estado operativo (solicitudes/subidas/aprobaciones).
-- Los documentos, versiones y chunks siguen en Delta/Unity Catalog.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS legajos;

-- Una fila por pedido de renovación de un documento de una entidad.
CREATE TABLE IF NOT EXISTS legajos.solicitudes (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cuit                 TEXT NOT NULL,
  razon_social         TEXT,
  tipo_documento       TEXT NOT NULL,
  motivo               TEXT,                       -- vencimiento | actualizacion
  estado               TEXT NOT NULL DEFAULT 'pendiente_envio',
                       -- pendiente_envio | notificado | subido | pendiente_aprobacion | aprobado | rechazado
  fecha_venc_doc       DATE,
  id_version_anterior  TEXT,
  resumen_anterior     TEXT,                       -- extracto de la versión vigente actual
  creado_en            TIMESTAMPTZ NOT NULL DEFAULT now(),
  actualizado_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Una fila por archivo que el cliente sube contra una solicitud (staging).
CREATE TABLE IF NOT EXISTS legajos.subidas (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  solicitud_id   UUID NOT NULL REFERENCES legajos.solicitudes(id) ON DELETE CASCADE,
  nombre_archivo TEXT NOT NULL,
  ruta_staging   TEXT NOT NULL,                    -- ruta en el Volume de staging
  file_hash      TEXT,
  validaciones   JSONB,                            -- {tipo_coincide, cuit_coincide, fecha_posterior}
  resumen_nuevo  TEXT,                             -- extracto del documento subido (parseo preliminar)
  subido_por     TEXT,
  subido_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Log de decisiones de Base Clientes (auditable: quién, cuándo, sobre qué).
CREATE TABLE IF NOT EXISTS legajos.aprobaciones (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  solicitud_id  UUID NOT NULL REFERENCES legajos.solicitudes(id) ON DELETE CASCADE,
  subida_id     UUID REFERENCES legajos.subidas(id),
  decision      TEXT NOT NULL,                     -- aprobado | rechazado
  motivo        TEXT,
  aprobado_por  TEXT,
  decidido_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_solicitudes_estado ON legajos.solicitudes(estado);
CREATE INDEX IF NOT EXISTS ix_subidas_solicitud  ON legajos.subidas(solicitud_id);
