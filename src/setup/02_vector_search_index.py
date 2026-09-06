# Databricks notebook source
# =============================================================================
# Vector Search · creación del índice Delta Sync (one-time, idempotente)
# Se corre UNA vez, después del primer refresh del pipeline. El mantenimiento
# incremental lo hace Delta Sync solo (TRIGGERED) leyendo el Change Data Feed
# de la tabla `chunks`. No se recrea el índice en cada corrida.
# =============================================================================
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import ResourceAlreadyExists

w = WorkspaceClient()

# --- Config ---
CATALOG        = "bind_ocr"
SCHEMA         = "legajos"
SOURCE_TABLE   = f"{CATALOG}.{SCHEMA}.chunks"
INDEX_NAME     = f"{CATALOG}.{SCHEMA}.chunks_index"
ENDPOINT_NAME  = "bind_ocr_vs"
# Embeddings MULTILINGÜE (corrige el gte-large-en inglés del notebook original).
# Verificar disponibilidad del endpoint en el workspace; alternativa: Model Serving propio.
EMBEDDING_MODEL = "databricks-qwen3-embedding-0-6b"
PRIMARY_KEY     = "chunk_id"
TEXT_COLUMN     = "texto_chunk"

# 1. Endpoint de Vector Search (si no existe).
try:
    w.vector_search_endpoints.create_endpoint(
        name=ENDPOINT_NAME, endpoint_type="STANDARD"
    )
    print(f"✓ Endpoint creado: {ENDPOINT_NAME}")
except ResourceAlreadyExists:
    print(f"✓ Endpoint ya existe: {ENDPOINT_NAME}")

# 2. Índice Delta Sync con embeddings gestionados.
#    columns_to_sync incluye ESTADO y fecha_vencimiento -> permite filtrar por
#    vigencia en la consulta (regla no negociable del diseño).
try:
    w.vector_search_indexes.create_index(
        name=INDEX_NAME,
        endpoint_name=ENDPOINT_NAME,
        primary_key=PRIMARY_KEY,
        index_type="DELTA_SYNC",
        delta_sync_index_spec={
            "source_table": SOURCE_TABLE,
            "pipeline_type": "TRIGGERED",
            "embedding_source_columns": [{
                "name": TEXT_COLUMN,
                "embedding_model_endpoint_name": EMBEDDING_MODEL,
            }],
            "columns_to_sync": [
                PRIMARY_KEY, "cuit", "razon_social", "tipo_documento",
                "estado", "id_version", "fecha_vencimiento", TEXT_COLUMN,
            ],
        },
    )
    print(f"✓ Índice creado: {INDEX_NAME}")
except ResourceAlreadyExists:
    print(f"✓ Índice ya existe: {INDEX_NAME}")

# 3. Disparar sync incremental (solo procesa el delta vía CDF).
w.vector_search_indexes.sync_index(index_name=INDEX_NAME)
print(f"✓ Sync disparado para {INDEX_NAME}")

# COMMAND ----------

# --- Prueba de consulta (filtrando por vigencia — nunca versiones reemplazadas) ---
resultados = w.vector_search_indexes.query_index(
    index_name=INDEX_NAME,
    columns=["cuit", "razon_social", "tipo_documento", "estado", "texto_chunk"],
    query_text="¿Qué facultades otorga el poder general?",
    filters_json='{"estado": "vigente"}',
    num_results=3,
)
print(resultados.result)
