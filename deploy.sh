#!/usr/bin/env bash
# =============================================================================
# Legajo Lakehouse · Script de despliegue completo
#
# Uso interactivo (te pregunta cada valor):
#   ./deploy.sh
#
# Uso con variables (sin prompts):
#   PROFILE=fe-sandbox-serverless TARGET=fe-sandbox-serverless \
#   CATALOG=bind_ocr SCHEMA=legajos WAREHOUSE_ID=abc123 \
#   ./deploy.sh
#
# Para Fase 3 (app + Lakebase), además:
#   PGHOST=ep-xxx.database.cloud.databricks.com PGUSER=tu@email.com \
#   DB_INSTANCE=legajo-lakehouse APP_NAME=legajo-lakehouse \
#   ./deploy.sh
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

# ---------- colores ----------
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓ $*${NC}"; }
info() { echo -e "${YELLOW}▶ $*${NC}"; }

# ---------- helper: preguntar si la variable no está en el entorno ----------
ask() {
  local var="$1" prompt="$2" default="${3:-}"
  if [[ -z "${!var:-}" ]]; then
    if [[ -n "$default" ]]; then
      read -rp "  $prompt [$default]: " val
      eval "$var=\"${val:-$default}\""
    else
      read -rp "  $prompt: " val
      eval "$var=\"$val\""
    fi
  fi
}

echo ""
echo "======================================================"
echo "  Legajo Lakehouse · Despliegue"
echo "======================================================"
echo ""
echo "Ingresá los parámetros del entorno destino."
echo "(Si ya los exportaste como variables de entorno, se saltan los prompts.)"
echo ""

# ---- Parámetros base ----
ask PROFILE       "Perfil CLI de Databricks"               "fe-sandbox-serverless"
ask TARGET        "Target del bundle (bind | fe-sandbox-serverless)" "fe-sandbox-serverless"
ask CATALOG       "Catálogo Unity Catalog destino"          "bind_ocr"
ask SCHEMA        "Schema destino"                          "legajos"
ask WAREHOUSE_ID  "ID del SQL warehouse serverless"

PYTHON="${PYTHON:-python3}"
VENV_PATH="${VENV_PATH:-/tmp/pdfvenv}"

echo ""
echo "------------------------------------------------------"
echo "  Perfil  : $PROFILE"
echo "  Target  : $TARGET"
echo "  Catálogo: $CATALOG"
echo "  Schema  : $SCHEMA"
echo "  Warehouse: $WAREHOUSE_ID"
echo "------------------------------------------------------"
echo ""

# ---- Verificar venv ----
if [[ ! -f "$VENV_PATH/bin/python3" ]]; then
  info "Creando venv en $VENV_PATH ..."
  python3 -m venv "$VENV_PATH"
  "$VENV_PATH/bin/pip" install -q databricks-sdk pymupdf reportlab psycopg[binary] pypdf
  ok "venv listo"
fi
PYTHON="$VENV_PATH/bin/python3"

# =============================================================================
# PASO 1 · Setup: catálogo, schema, volume, maestro
# =============================================================================
info "PASO 1 · Setup de catálogo, schema, volumen y maestro..."
$PYTHON run_sql.py src/setup/01_setup_catalogo.sql \
  --profile "$PROFILE" \
  --warehouse "$WAREHOUSE_ID" \
  --catalog "$CATALOG" \
  --schema "$SCHEMA"
ok "Setup completado"

# =============================================================================
# PASO 2 · Generar y subir documentos simulados
# =============================================================================
info "PASO 2 · Generando PDFs simulados..."
$PYTHON docs_simulados/generar_documentos.py
ok "PDFs generados en docs_simulados/out/"

info "Subiendo documentos al Volume..."
bash subir_documentos.sh "$PROFILE" "$CATALOG" "$SCHEMA"
ok "Documentos subidos"

# =============================================================================
# PASO 3 · Desplegar y correr el pipeline (Lakeflow)
# =============================================================================
info "PASO 3 · Validando bundle..."
databricks bundle validate -p "$PROFILE" -t "$TARGET" \
  --var="catalog=$CATALOG" --var="schema=$SCHEMA"

info "Desplegando bundle..."
databricks bundle deploy -p "$PROFILE" -t "$TARGET" \
  --var="catalog=$CATALOG" --var="schema=$SCHEMA"

info "Corriendo el pipeline..."
databricks bundle run legajos_pipeline -p "$PROFILE" -t "$TARGET" \
  --var="catalog=$CATALOG" --var="schema=$SCHEMA"
ok "Pipeline completado"

# Capturar el PIPELINE_ID desde el deployment.json generado por el bundle
PIPELINE_ID=$(python3 -c "
import json, sys
path = '.databricks/bundle/$TARGET/deployment.json'
d = json.load(open(path))
print(d['resources']['pipelines']['legajos_pipeline']['id'])
" 2>/dev/null || echo "")

if [[ -n "$PIPELINE_ID" ]]; then
  ok "Pipeline ID: $PIPELINE_ID"
else
  echo ""
  read -rp "  No se pudo leer el Pipeline ID automáticamente. Ingresalo manualmente: " PIPELINE_ID
fi

# =============================================================================
# PASO 4 · Vector Search: endpoint + índice
# =============================================================================
info "PASO 4 · Creando endpoint e índice Vector Search..."
$PYTHON vs_deploy.py \
  --profile "$PROFILE" \
  --catalog "$CATALOG" \
  --schema "$SCHEMA"
ok "Vector Search listo"

# =============================================================================
# PASO 5 · Verificar consultas en el índice
# =============================================================================
info "PASO 5 · Verificando consultas de prueba..."
$PYTHON vs_query.py \
  --profile "$PROFILE" \
  --catalog "$CATALOG" \
  --schema "$SCHEMA"
ok "Consultas verificadas"

# =============================================================================
# PASO 6 (opcional) · Fase 3: Lakebase + App
# =============================================================================
echo ""
read -rp "¿Desplegar Fase 3 (App + Lakebase)? [s/N]: " DEPLOY_FASE3
if [[ "${DEPLOY_FASE3,,}" != "s" ]]; then
  echo ""
  ok "Despliegue base completado. Fase 3 omitida."
  echo "  Para desplegar Fase 3 más adelante, pasá PIPELINE_ID=$PIPELINE_ID"
  exit 0
fi

echo ""
ask PGHOST      "Host de la instancia Lakebase"
ask PGUSER      "Usuario Lakebase (email Databricks)"  "miguel.jimenez@databricks.com"
ask DB_INSTANCE "Nombre de la instancia Lakebase"      "legajo-lakehouse"
ask APP_NAME    "Nombre de la Databricks App"           "legajo-lakehouse"
ask APP_PATH    "Ruta en el workspace para la app (sin /Workspace/)"  "Users/$PGUSER/legajo-lakehouse-app"

info "Creando schema Lakebase (solicitudes / subidas / aprobaciones)..."
$PYTHON fase3/run_pg.py fase3/01_schema_lakebase.sql \
  --profile "$PROFILE" \
  --host "$PGHOST" \
  --user "$PGUSER"
ok "Schema Lakebase creado"

info "Creando Volume staging en Unity Catalog..."
$PYTHON run_sql.py fase3/02_setup_staging.sql \
  --profile "$PROFILE" \
  --warehouse "$WAREHOUSE_ID" \
  --catalog "$CATALOG" \
  --schema "$SCHEMA"
ok "Volume staging creado"

info "Sembrando solicitudes de prueba..."
$PYTHON fase3/seed_solicitudes.py \
  --profile "$PROFILE" \
  --warehouse "$WAREHOUSE_ID" \
  --catalog "$CATALOG" \
  --schema "$SCHEMA" \
  --pghost "$PGHOST" \
  --pguser "$PGUSER" \
  --estado notificado
ok "Solicitudes sembradas"

# Actualizar app.yaml con los valores del entorno
info "Actualizando fase3/app/app.yaml..."
sed -i.bak \
  -e "s|value: \"\"   # completar con el ID del pipeline.*|value: \"$PIPELINE_ID\"|" \
  -e "s|value: \"\"   # ej: /Volumes/<catalog>/<schema>/staging|value: \"/Volumes/$CATALOG/$SCHEMA/staging\"|" \
  -e "s|value: \"\"   # ej: /Volumes/<catalog>/<schema>/documentacion|value: \"/Volumes/$CATALOG/$SCHEMA/documentacion\"|" \
  -e "s|value: \"\"   # nombre de la instancia Lakebase.*|value: \"$DB_INSTANCE\"|" \
  -e "s|value: \"ep-rough-breeze.*\"|value: \"$PGHOST\"|" \
  fase3/app/app.yaml
ok "app.yaml actualizado"

info "Sincronizando código de la app al workspace..."
databricks sync fase3/app "$APP_PATH" -p "$PROFILE" --full

info "Desplegando Databricks App..."
databricks apps deploy "$APP_NAME" \
  --source-code-path "/Workspace/$APP_PATH" \
  -p "$PROFILE"
ok "App desplegada"

# Obtener el SP de la app y darle permisos en el schema Lakebase
info "Obteniendo service principal de la app..."
SP_NUM=$(databricks apps get "$APP_NAME" -p "$PROFILE" --output json | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['service_principal_id'])")
SP_APPID=$(databricks service-principals get "$SP_NUM" -p "$PROFILE" --output json | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['applicationId'])")
ok "SP application ID: $SP_APPID"

info "Otorgando permisos en Lakebase schema legajos al SP de la app..."
$PYTHON fase3/run_pg.py \
  --profile "$PROFILE" \
  --host "$PGHOST" \
  --user "$PGUSER" \
  --sql "
GRANT USAGE  ON SCHEMA legajos TO \"$SP_APPID\";
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA legajos TO \"$SP_APPID\";
"
ok "Permisos Lakebase otorgados a $SP_APPID"

info "Otorgando permisos UC al SP de la app (catálogo, schema, volumes)..."
databricks grants update catalog "$CATALOG" -p "$PROFILE" \
  --json "{\"changes\":[{\"principal\":\"$SP_APPID\",\"add\":[\"USE_CATALOG\"]}]}" > /dev/null
ok "  USE_CATALOG → $CATALOG"
databricks grants update schema "${CATALOG}.${SCHEMA}" -p "$PROFILE" \
  --json "{\"changes\":[{\"principal\":\"$SP_APPID\",\"add\":[\"USE_SCHEMA\"]}]}" > /dev/null
ok "  USE_SCHEMA → ${CATALOG}.${SCHEMA}"

for VOL in staging documentacion; do
  databricks grants update volume "${CATALOG}.${SCHEMA}.${VOL}" -p "$PROFILE" \
    --json "{\"changes\":[{\"principal\":\"$SP_APPID\",\"add\":[\"READ_VOLUME\",\"WRITE_VOLUME\"]}]}" \
    > /dev/null
  ok "  READ_VOLUME + WRITE_VOLUME → ${CATALOG}.${SCHEMA}.${VOL}"
done

info "Otorgando CAN_RUN en el pipeline al SP de la app..."
databricks pipelines update-permissions "$PIPELINE_ID" -p "$PROFILE" \
  --json "{\"access_control_list\":[{\"service_principal_name\":\"$SP_APPID\",\"permission_level\":\"CAN_RUN\"}]}" \
  > /dev/null
ok "CAN_RUN → pipeline $PIPELINE_ID"

echo ""
echo "======================================================"
ok "Despliegue completo."
echo ""
echo "  Pipeline ID : $PIPELINE_ID"
echo "  App         : $APP_NAME"
echo "  Catálogo    : $CATALOG.$SCHEMA"
echo "======================================================"
