#!/usr/bin/env python3
"""
Genera documentos para 2 entidades nuevas del demo:
  - Banco Regional del Norte S.A.  (CUIT 30823456789)
  - Fintech Mercado Sur S.A.S.     (CUIT 30934567890)

Salida: docs_simulados/demo/entidades_nuevas/
Estados esperados en el pipeline:
  - banco / poder          -> vencido  (demo portal renovación)
  - banco / estatuto       -> vigente  (demo inventario)
  - fintech / constancia   -> por_vencer ~38 días (demo alerta próxima)
  - fintech / estados_cont -> vigente  (demo inventario)
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

OUT = os.path.join(os.path.dirname(__file__), "demo", "entidades_nuevas")
os.makedirs(OUT, exist_ok=True)

styles = getSampleStyleSheet()
H    = ParagraphStyle("H",    parent=styles["Title"],    fontSize=15, spaceAfter=14, textColor=colors.HexColor("#1B3139"))
SUB  = ParagraphStyle("SUB",  parent=styles["Heading2"], fontSize=11, textColor=colors.HexColor("#C4260F"))
BODY = ParagraphStyle("BODY", parent=styles["BodyText"], fontSize=10, leading=15, alignment=4)
SMALL= ParagraphStyle("SMALL",parent=styles["BodyText"], fontSize=8,  textColor=colors.grey)

def fmt_cuit(c): return f"{c[:2]}-{c[2:10]}-{c[10:]}"

def build(filename, title, subtitle, paragraphs, footer):
    path = os.path.join(OUT, filename)
    doc = SimpleDocTemplate(path, pagesize=A4,
                            topMargin=2.2*cm, bottomMargin=2*cm,
                            leftMargin=2.5*cm, rightMargin=2.5*cm)
    story = [Paragraph(title, H), Paragraph(subtitle, SUB), Spacer(1, 14)]
    for p in paragraphs:
        story.append(p if isinstance(p, Table) else Paragraph(p, BODY))
        story.append(Spacer(1, 8))
    story.append(Spacer(1, 20))
    story.append(Paragraph(footer, SMALL))
    doc.build(story)
    print(f"  ✓ {filename}")

def kv(rows):
    t = Table(rows, colWidths=[5*cm, 9*cm])
    t.setStyle(TableStyle([
        ("FONTSIZE",    (0,0),(-1,-1), 9),
        ("TEXTCOLOR",   (0,0),(0,-1), colors.HexColor("#1B3139")),
        ("FONTNAME",    (0,0),(0,-1), "Helvetica-Bold"),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LINEBELOW",   (0,0),(-1,-1), 0.4, colors.HexColor("#DAD5CD")),
    ]))
    return t

print("Generando documentos para entidades nuevas del demo...")

# ── Banco Regional del Norte S.A. ─────────────────────────────────────────
BANCO = "30823456789"
BANCO_RS = "Banco Regional del Norte S.A."

# 1. PODER — VENCIDO (para el portal de renovación)
build(
    f"{BANCO}_poder_apoderado_comercial.pdf",
    "PODER ESPECIAL COMERCIAL",
    BANCO_RS,
    [
        kv([
            ["Otorgante:",         BANCO_RS],
            ["CUIT otorgante:",    fmt_cuit(BANCO)],
            ["Apoderado:",         "Sebastián Torres, DNI 31.445.678"],
            ["Fecha de otorgamiento:", "10/03/2023"],
            ["Vigencia hasta:",    "10/03/2025"],
        ]),
        "BANCO REGIONAL DEL NORTE S.A. otorga poder especial comercial a favor del Sr. Sebastián Torres "
        "para representar a la entidad ante proveedores, clientes corporativos y organismos de contralor "
        "bancario en la Región NOA.",
        "El presente poder especial vence el 10/03/2025 y no es renovable automáticamente.",
    ],
    "Poder especial. Escritura N° 88, Registro Notarial 22 Salta. Emitido el 10/03/2023.",
)

# 2. ESTATUTO — VIGENTE (sin vencimiento)
build(
    f"{BANCO}_estatuto_social.pdf",
    "ESTATUTO SOCIAL",
    BANCO_RS,
    [
        kv([
            ["Razón social:",      BANCO_RS],
            ["CUIT:",              fmt_cuit(BANCO)],
            ["Tipo societario:",   "Sociedad Anónima"],
            ["Fecha de constitución:", "22/08/2005"],
            ["Inscripción CNV:",   "N° 1102, autorizada por Resolución 18.432/2005"],
        ]),
        "<b>ARTÍCULO PRIMERO.</b> Se constituye BANCO REGIONAL DEL NORTE S.A., entidad financiera "
        "autorizada por el Banco Central de la República Argentina para operar como banco comercial "
        "con domicilio social en la ciudad de Salta.",
        "<b>ARTÍCULO SEGUNDO — OBJETO.</b> Realizar todas las operaciones activas, pasivas y de servicios "
        "permitidas a los bancos comerciales por la Ley 21.526 de Entidades Financieras.",
        "<b>ARTÍCULO TERCERO — CAPITAL.</b> El capital social se fija en PESOS QUINIENTOS MILLONES "
        "($500.000.000), integrado en un 100% al momento de la constitución.",
    ],
    "Estatuto actualizado conforme última asamblea extraordinaria del 15/06/2022.",
)

# ── Fintech Mercado Sur S.A.S. ────────────────────────────────────────────
FINTECH = "30934567890"
FINTECH_RS = "Fintech Mercado Sur S.A.S."

# 3. CONSTANCIA AFIP — POR VENCER en ~38 días (vence 15/10/2026)
build(
    f"{FINTECH}_constancia_inscripcion_afip.pdf",
    "CONSTANCIA DE INSCRIPCIÓN",
    "AFIP · Administración Federal de Ingresos Públicos",
    [
        kv([
            ["Denominación:",      FINTECH_RS],
            ["CUIT:",              fmt_cuit(FINTECH)],
            ["Fecha de emisión:",  "18/04/2026"],
            ["Impuestos:",         "IVA · Ganancias · Monotributo Categoría H"],
            ["Actividad principal:","631900 - Otras actividades de tecnología de la información"],
            ["Domicilio fiscal:",  "Av. Corrientes 5800, CABA"],
        ]),
        "La Administración Federal de Ingresos Públicos certifica la inscripción del contribuyente "
        "en los tributos indicados a la fecha de emisión.",
        "Esta constancia tiene validez de CIENTO OCHENTA (180) días corridos. Fecha de vencimiento: 15/10/2026.",
    ],
    "Constancia AFIP emitida el 18/04/2026. Vence el 15/10/2026 (por vencer en ~38 días).",
)

# 4. ESTADOS CONTABLES — VIGENTE (cierre 31/12/2025, vence por regla 31/12/2026)
build(
    f"{FINTECH}_estados_contables_2025.pdf",
    "ESTADOS CONTABLES",
    FINTECH_RS,
    [
        kv([
            ["Razón social:",  FINTECH_RS],
            ["CUIT:",          fmt_cuit(FINTECH)],
            ["Ejercicio N°:",  "5"],
            ["Fecha de cierre:", "31/12/2025"],
            ["Fecha de emisión:", "28/02/2026"],
        ]),
        "Estados contables del ejercicio económico finalizado el 31 de diciembre de 2025, "
        "conforme normas contables profesionales (RT 26 y modificatorias), expresados en moneda homogénea.",
        "<b>ESTADO DE SITUACIÓN PATRIMONIAL.</b> Activo total: $ 42.180.000. "
        "Pasivo total: $ 18.340.000. Patrimonio neto: $ 23.840.000.",
        "<b>ESTADO DE RESULTADOS.</b> Ingresos por servicios: $ 91.500.000. "
        "Resultado del ejercicio (ganancia): $ 7.920.000.",
        "Auditoría externa: opinión favorable sin salvedades.",
    ],
    "Balance ejercicio cerrado 31/12/2025. Vigente por 12 meses desde el cierre (vence 31/12/2026).",
)

print(f"\nListo. 4 documentos en: {OUT}")
print("\nEstados esperados tras el pipeline:")
print("  30823456789 / poder              -> VENCIDO   (vence 10/03/2025)  → portal renovación")
print("  30823456789 / estatuto           -> VIGENTE   (sin vencimiento)")
print("  30934567890 / constancia_inscripcion -> POR_VENCER (vence 15/10/2026 ~38 días)")
print("  30934567890 / estados_contables  -> VIGENTE   (vence 31/12/2026 por regla)")
