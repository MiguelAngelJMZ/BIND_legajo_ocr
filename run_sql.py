#!/usr/bin/env python3
"""Ejecuta un archivo .sql (statements separados por ';') contra un SQL warehouse.
Uso: run_sql.py <archivo.sql> --profile <perfil> --warehouse <id> [--catalog X] [--schema Y]
     run_sql.py --sql "SELECT 1"  --profile <perfil> --warehouse <id>
Reemplaza {catalog} y {schema} en el SQL con los valores pasados por argumento."""
import sys, argparse, re
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

ap = argparse.ArgumentParser()
ap.add_argument("sqlfile", nargs="?")
ap.add_argument("--profile",   required=True, help="Perfil CLI de Databricks")
ap.add_argument("--warehouse", required=True, help="ID del SQL warehouse serverless")
ap.add_argument("--sql",       default=None,  help="SQL inline en vez de archivo")
ap.add_argument("--catalog",   default="",    help="Reemplaza {catalog} en el SQL")
ap.add_argument("--schema",    default="",    help="Reemplaza {schema} en el SQL")
args = ap.parse_args()

w = WorkspaceClient(profile=args.profile)
raw = args.sql if args.sql else open(args.sqlfile).read()

raw = raw.replace("{catalog}", args.catalog).replace("{schema}", args.schema)

# quita comentarios de línea (-- ...) antes de separar por ';'
sql = "\n".join(l for l in raw.splitlines() if not l.lstrip().startswith("--"))
stmts = [s.strip() for s in sql.split(";") if s.strip()]

for i, stmt in enumerate(stmts, 1):
    first = " ".join(stmt.split()[:6])
    print(f"[{i}/{len(stmts)}] {first} ...", flush=True)
    r = w.statement_execution.execute_statement(
        warehouse_id=args.warehouse, statement=stmt, wait_timeout="50s"
    )
    st = r.status.state
    if st != StatementState.SUCCEEDED:
        print(f"   ✗ {st}: {r.status.error.message if r.status.error else ''}")
        sys.exit(1)
    if r.result and r.result.data_array:
        for row in r.result.data_array[:20]:
            print("   ", row)
    print("   ✓")
print("OK")
