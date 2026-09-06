#!/usr/bin/env python3
"""Crea endpoint + índice Delta Sync y dispara el sync. Polling incluido.
Uso: vs_deploy.py --profile <perfil> --catalog <catalogo> --schema <schema>
                  [--endpoint <nombre>] [--embedding <endpoint>]"""
import time, sys, argparse
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import ResourceAlreadyExists, AlreadyExists

_EXISTS = (ResourceAlreadyExists, AlreadyExists)
from databricks.sdk.service.vectorsearch import (
    EndpointType, VectorIndexType, DeltaSyncVectorIndexSpecRequest,
    EmbeddingSourceColumn, PipelineType,
)

ap = argparse.ArgumentParser()
ap.add_argument("--profile",   required=True, help="Perfil CLI de Databricks")
ap.add_argument("--catalog",   required=True, help="Catálogo Unity Catalog")
ap.add_argument("--schema",    required=True, help="Schema destino")
ap.add_argument("--endpoint",  default=None,  help="Nombre del endpoint VS (default: <catalog>_vs)")
ap.add_argument("--embedding", default="databricks-qwen3-embedding-0-6b",
                               help="Endpoint de embeddings multilingüe")
args = ap.parse_args()

w = WorkspaceClient(profile=args.profile)

SOURCE_TABLE  = f"{args.catalog}.{args.schema}.chunks"
INDEX_NAME    = f"{args.catalog}.{args.schema}.chunks_index"
ENDPOINT_NAME = args.endpoint or f"{args.catalog}_vs"
EMBEDDING     = args.embedding
PK, TEXTCOL   = "chunk_key", "texto_chunk"

print(f"SOURCE_TABLE : {SOURCE_TABLE}")
print(f"INDEX_NAME   : {INDEX_NAME}")
print(f"ENDPOINT_NAME: {ENDPOINT_NAME}")
print(f"EMBEDDING    : {EMBEDDING}")

# 1. Endpoint
try:
    w.vector_search_endpoints.create_endpoint(name=ENDPOINT_NAME, endpoint_type=EndpointType.STANDARD)
    print(f"✓ endpoint solicitado: {ENDPOINT_NAME}")
except _EXISTS:
    print(f"✓ endpoint ya existe: {ENDPOINT_NAME}")

print("esperando ONLINE del endpoint...", flush=True)
for i in range(60):
    e = w.vector_search_endpoints.get_endpoint(ENDPOINT_NAME)
    st = e.endpoint_status.state.value if e.endpoint_status else "?"
    print(f"  [{i}] {st}", flush=True)
    if st == "ONLINE":
        break
    time.sleep(20)

# 2. Índice
try:
    w.vector_search_indexes.create_index(
        name=INDEX_NAME, endpoint_name=ENDPOINT_NAME, primary_key=PK,
        index_type=VectorIndexType.DELTA_SYNC,
        delta_sync_index_spec=DeltaSyncVectorIndexSpecRequest(
            source_table=SOURCE_TABLE,
            pipeline_type=PipelineType.TRIGGERED,
            embedding_source_columns=[EmbeddingSourceColumn(
                name=TEXTCOL, embedding_model_endpoint_name=EMBEDDING)],
            columns_to_sync=[PK, "cuit", "razon_social", "tipo_documento",
                             "estado", "id_version", "fecha_vencimiento", "chunk_idx", TEXTCOL],
        ),
    )
    print(f"✓ índice creado: {INDEX_NAME}")
except _EXISTS:
    print(f"✓ índice ya existe: {INDEX_NAME}")
    w.vector_search_indexes.sync_index(index_name=INDEX_NAME)

print("esperando que el índice quede READY...", flush=True)
for i in range(60):
    s = w.vector_search_indexes.get_index(INDEX_NAME).status
    ready = s.ready if s else False
    print(f"  [{i}] ready={ready} rows={getattr(s,'indexed_row_count',None)} :: {getattr(s,'message','')}", flush=True)
    if ready:
        break
    time.sleep(20)
print("LISTO")
