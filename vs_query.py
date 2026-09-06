#!/usr/bin/env python3
"""Espera a que el índice quede READY y corre consultas de prueba.
Uso: vs_query.py --profile <perfil> --catalog <catalogo> --schema <schema>"""
import time, argparse
from databricks.sdk import WorkspaceClient

ap = argparse.ArgumentParser()
ap.add_argument("--profile", required=True, help="Perfil CLI de Databricks")
ap.add_argument("--catalog", required=True, help="Catálogo Unity Catalog")
ap.add_argument("--schema",  required=True, help="Schema destino")
args = ap.parse_args()

w = WorkspaceClient(profile=args.profile)
IDX = f"{args.catalog}.{args.schema}.chunks_index"

for i in range(90):
    s = w.vector_search_indexes.get_index(IDX).status
    print(f"[{i}] ready={s.ready} rows={getattr(s,'indexed_row_count',None)} :: {getattr(s,'message','')}", flush=True)
    if s.ready:
        break
    time.sleep(20)

def q(texto, filtros=None):
    r = w.vector_search_indexes.query_index(
        index_name=IDX,
        columns=["cuit", "razon_social", "tipo_documento", "estado", "texto_chunk"],
        query_text=texto,
        filters_json=filtros,
        num_results=3,
    )
    print(f"\n=== '{texto}'  filtro={filtros} ===")
    for row in (r.result.data_array or []):
        print(f"  {row[1]:28} | {row[2]:24} | {row[3]:10} | {row[4][:70]!r}")

q("¿Qué facultades otorga el poder general?", '{"estado": "vigente"}')
q("objeto social y capital del estatuto")
q("balance y estados contables", '{"tipo_documento": "estados_contables"}')
print("\nLISTO")
