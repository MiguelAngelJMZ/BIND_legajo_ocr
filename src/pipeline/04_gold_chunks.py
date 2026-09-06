# =============================================================================
# GOLD · chunks_stream (STREAMING) — explode de texto en chunks por fila.
# Alimenta el AUTO CDC de `chunks` (05_gold_chunks_cdc.sql).
#
# RETIRO DE HUÉRFANOS: cuando una versión nueva produce MENOS chunks que la
# anterior, los slots sobrantes (idx alto) de la versión vieja quedarían huérfanos
# en el índice. Para retirarlos, además de los chunks reales emitimos filas de
# RETIRO (_op='delete') para los slots [N, MAX_SLOTS). El AUTO CDC las borra por
# clave. Así ninguna versión reemplazada deja chunks colgados.
# =============================================================================
import dlt
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, StringType

CHUNK_SIZE, CHUNK_OVERLAP = 900, 150
MAX_SLOTS = 50   # cota superior de chunks por documento (para retirar huérfanos)

_COLS = ["cuit", "razon_social", "tipo_documento", "estado", "id_version",
         "fecha_vencimiento", "file_modification_time", "chunk_idx",
         "texto_chunk", "chunk_key", "_op"]


def _chunk_text(texto, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    if not texto:
        return []
    parrafos = [p.strip() for p in texto.split("\n\n") if p.strip()]
    chunks, actual = [], ""
    for p in parrafos:
        if len(actual) + len(p) + 2 <= size:
            actual = (actual + "\n\n" + p) if actual else p
        else:
            if actual:
                chunks.append(actual)
            if len(p) > size:
                start = 0
                while start < len(p):
                    chunks.append(p[start:start + size])
                    start += size - overlap
                actual = ""
            else:
                actual = p
    if actual:
        chunks.append(actual)
    return chunks


chunk_udf = F.udf(_chunk_text, ArrayType(StringType()))


@dlt.table(
    name="chunks_stream",
    comment="Chunks explotados por fila (upsert) + retiros de slots huérfanos (delete).",
    table_properties={"delta.enableChangeDataFeed": "true"},
)
def chunks_stream():
    base = dlt.read_stream("documentos_norm").withColumn("_chunks", chunk_udf(F.col("texto_completo")))

    # UPSERT: una fila por chunk real de la versión.
    upserts = (
        base
        .select("cuit", "razon_social", "tipo_documento", "estado", "id_version",
                "fecha_vencimiento", "file_modification_time",
                F.posexplode("_chunks").alias("chunk_idx", "texto_chunk"))
        .withColumn("chunk_key", F.concat_ws("|", "cuit", "tipo_documento",
                                             F.col("chunk_idx").cast("string")))
        .withColumn("_op", F.lit("upsert"))
        .select(*_COLS)
    )

    # DELETE: retirar slots [N, MAX_SLOTS) que esta versión ya no ocupa.
    deletes = (
        base
        .withColumn("_n", F.size("_chunks"))
        .withColumn("chunk_idx", F.explode(F.sequence(F.lit(0), F.lit(MAX_SLOTS - 1))))
        .filter(F.col("chunk_idx") >= F.col("_n"))
        .withColumn("chunk_key", F.concat_ws("|", "cuit", "tipo_documento",
                                             F.col("chunk_idx").cast("string")))
        .withColumn("texto_chunk", F.lit(None).cast("string"))
        .withColumn("_op", F.lit("delete"))
        .select(*_COLS)
    )

    return upserts.unionByName(deletes)
