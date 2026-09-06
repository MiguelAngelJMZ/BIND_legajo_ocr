#!/usr/bin/env bash
# Sube los PDFs simulados al Volume (simula la ingesta ya resuelta).
# Uso:  ./subir_documentos.sh <perfil> <catalogo> <schema>
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Uso: $0 <perfil> <catalogo> <schema>"
  exit 1
fi

PROFILE="$1"
CATALOG="$2"
SCHEMA="$3"
VOLUME="/Volumes/${CATALOG}/${SCHEMA}/documentacion"
SRC="$(dirname "$0")/docs_simulados/out"

echo "Subiendo documentos de $SRC -> $VOLUME (perfil: $PROFILE)"
for f in "$SRC"/*.pdf; do
  nombre="$(basename "$f")"
  databricks fs cp "$f" "dbfs:${VOLUME}/${nombre}" --overwrite -p "$PROFILE"
  echo "  ✓ $nombre"
done

echo "Listo. Contenido del volumen:"
databricks fs ls "dbfs:${VOLUME}" -p "$PROFILE"
