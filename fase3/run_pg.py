#!/usr/bin/env python3
"""Ejecuta un .sql contra Lakebase (Postgres). Password = token OAuth del perfil.
Uso: run_pg.py <archivo.sql> --profile <perfil> --host <lakebase_host> --user <email>
     run_pg.py --sql "SELECT 1"  --profile <perfil> --host <lakebase_host> --user <email>"""
import sys, argparse
import psycopg
from databricks.sdk import WorkspaceClient

ap = argparse.ArgumentParser()
ap.add_argument("sqlfile", nargs="?")
ap.add_argument("--profile", required=True, help="Perfil CLI de Databricks")
ap.add_argument("--sql",     default=None,  help="SQL inline en vez de archivo")
ap.add_argument("--host",    required=True, help="Host de la instancia Lakebase")
ap.add_argument("--user",    required=True, help="Usuario Postgres (email Databricks)")
ap.add_argument("--db",      default="databricks_postgres")
args = ap.parse_args()

w = WorkspaceClient(profile=args.profile)
token = w.config.oauth_token().access_token   # token OAuth U2M como password de Postgres

conn = psycopg.connect(host=args.host, port=5432, dbname=args.db, user=args.user,
                       password=token, sslmode="require", autocommit=True)
print(f"conectado a {args.host}/{args.db} como {args.user}")

script = args.sql if args.sql else open(args.sqlfile).read()
with conn.cursor() as cur:
    cur.execute(script)
    try:
        rows = cur.fetchall()
        for r in rows:
            print("  ", r)
    except psycopg.ProgrammingError:
        pass
print("OK")
conn.close()
