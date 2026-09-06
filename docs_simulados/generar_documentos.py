#!/usr/bin/env python3
"""
Generador de documentación societaria argentina SIMULADA para el POC Legajo Lakehouse.

Crea ~10 PDFs de distintos tipos (estatuto, poder, acta, constancia AFIP, balance,
informe crediticio) para 4 personas jurídicas ficticias. Los casos están diseñados
para ejercer las 3 vías de resolución de entidad del diseño:

  - CUIT en el nombre de archivo         -> match determinístico (nivel 1-2)
  - CUIT solo dentro del contenido       -> match por contenido (nivel 3)
  - sin CUIT en ningún lado              -> cola de revisión (nivel 4)

Salida: PDFs en ./out/  (nombres tal como "llegarían" al Volume).
Ejecutar:  python generar_documentos.py
"""
import os
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)

# --- Maestro de entidades ficticias (semilla para bind_ocr.legajos.personas_juridicas) ---
ENTIDADES = {
    "30712345678": "Estancias del Sur S.A.",
    "30709876543": "Logística Andina S.R.L.",
    "33698765439": "Grupo Textil Paraná S.A.",
    "30715558882": "Consultora Rivadavia S.A.S.",  # entidad con caso de review
}

styles = getSampleStyleSheet()
H = ParagraphStyle("H", parent=styles["Title"], fontSize=15, spaceAfter=14, textColor=colors.HexColor("#1B3139"))
SUB = ParagraphStyle("SUB", parent=styles["Heading2"], fontSize=11, textColor=colors.HexColor("#C4260F"))
BODY = ParagraphStyle("BODY", parent=styles["BodyText"], fontSize=10, leading=15, alignment=4)
SMALL = ParagraphStyle("SMALL", parent=styles["BodyText"], fontSize=8, textColor=colors.grey)


def fmt_cuit(c):
    return f"{c[:2]}-{c[2:10]}-{c[10:]}"


def build(filename, title, subtitle, paragraphs, footer):
    path = os.path.join(OUT, filename)
    doc = SimpleDocTemplate(path, pagesize=A4,
                            topMargin=2.2*cm, bottomMargin=2*cm,
                            leftMargin=2.5*cm, rightMargin=2.5*cm)
    story = [Paragraph(title, H), Paragraph(subtitle, SUB), Spacer(1, 14)]
    for p in paragraphs:
        if isinstance(p, Table):
            story.append(p)
        else:
            story.append(Paragraph(p, BODY))
        story.append(Spacer(1, 8))
    story.append(Spacer(1, 20))
    story.append(Paragraph(footer, SMALL))
    doc.build(story)
    print(f"  ✓ {filename}")


def kv_table(rows):
    t = Table(rows, colWidths=[5*cm, 9*cm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1B3139")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#DAD5CD")),
    ]))
    return t


# =========================================================================
#  DOCUMENTOS
# =========================================================================
print("Generando documentos simulados...")

# 1. ESTATUTO — CUIT en filename (match determinístico)
c = "30712345678"
build(
    f"{c}_estatuto_social.pdf",
    "ESTATUTO SOCIAL",
    ENTIDADES[c],
    [
        kv_table([
            ["Razón social:", ENTIDADES[c]],
            ["CUIT:", fmt_cuit(c)],
            ["Tipo societario:", "Sociedad Anónima"],
            ["Fecha de constitución:", "14/03/2018"],
            ["Inscripción IGJ:", "N° 4521, Libro 89, Tomo -, 22/03/2018"],
        ]),
        "<b>ARTÍCULO PRIMERO.</b> Bajo la denominación de ESTANCIAS DEL SUR S.A. se constituye "
        "una sociedad anónima con domicilio legal en la Ciudad Autónoma de Buenos Aires, "
        "República Argentina.",
        "<b>ARTÍCULO SEGUNDO — OBJETO.</b> La sociedad tiene por objeto realizar por cuenta propia, "
        "de terceros o asociada a terceros, las siguientes actividades: explotación agropecuaria, "
        "ganadera, agrícola, forestal y de granja; compra, venta, arrendamiento y administración "
        "de establecimientos rurales; y la comercialización de sus productos y subproductos.",
        "<b>ARTÍCULO TERCERO — CAPITAL.</b> El capital social se fija en la suma de PESOS DIEZ "
        "MILLONES ($10.000.000), representado por diez mil acciones ordinarias nominativas no "
        "endosables de valor nominal mil pesos cada una.",
        "<b>ARTÍCULO DÉCIMO — DURACIÓN.</b> El plazo de duración de la sociedad se establece en "
        "noventa y nueve (99) años contados desde la fecha de inscripción en el Registro Público.",
    ],
    "Documento societario. Escritura N° 112, Registro Notarial 45 CABA. Emitido el 14/03/2018.",
)

# 2. PODER — CUIT en filename (determinístico), con fecha de vencimiento
c = "30712345678"
build(
    f"{c}_poder_general.pdf",
    "PODER GENERAL AMPLIO DE ADMINISTRACIÓN Y DISPOSICIÓN",
    ENTIDADES[c],
    [
        kv_table([
            ["Otorgante:", ENTIDADES[c]],
            ["CUIT otorgante:", fmt_cuit(c)],
            ["Apoderado:", "Juan Alberto Méndez, DNI 24.876.123"],
            ["Fecha de otorgamiento:", "05/06/2023"],
            ["Vigencia hasta:", "05/06/2026"],
        ]),
        "En la Ciudad de Buenos Aires, a los cinco días del mes de junio de 2023, comparece el "
        "representante legal de ESTANCIAS DEL SUR S.A. y CONFIERE PODER GENERAL AMPLIO a favor "
        "del señor Juan Alberto Méndez para que en nombre y representación de la sociedad ejerza "
        "las siguientes facultades:",
        "<b>a)</b> Representar a la sociedad ante organismos nacionales, provinciales y municipales, "
        "AFIP, ARCA, IGJ, ANSES y entidades bancarias. <b>b)</b> Operar cuentas corrientes y "
        "cajas de ahorro, librar y endosar cheques. <b>c)</b> Celebrar contratos de compraventa, "
        "locación y mutuo. <b>d)</b> Otorgar y revocar poderes especiales.",
        "El presente poder tendrá una vigencia de TRES (3) años a partir de la fecha de "
        "otorgamiento, venciendo en consecuencia el 05/06/2026, sin perjuicio de su revocación "
        "anticipada por parte del otorgante.",
    ],
    "Poder. Escritura N° 340, Registro Notarial 12 CABA. Fecha de emisión 05/06/2023.",
)

# 3. ACTA DE DESIGNACIÓN — CUIT en filename
c = "30709876543"
build(
    f"{c}_acta_designacion_autoridades.pdf",
    "ACTA DE ASAMBLEA GENERAL ORDINARIA",
    ENTIDADES[c],
    [
        kv_table([
            ["Razón social:", ENTIDADES[c]],
            ["CUIT:", fmt_cuit(c)],
            ["Tipo de asamblea:", "General Ordinaria"],
            ["Fecha de celebración:", "28/04/2024"],
            ["Acta N°:", "37"],
        ]),
        "En la sede social de LOGÍSTICA ANDINA S.R.L., siendo las 10:00 horas del día 28 de abril "
        "de 2024, se reúnen los socios que representan el 100% del capital social a fin de tratar "
        "el siguiente orden del día: designación de gerentes por vencimiento de mandato.",
        "Se resuelve por unanimidad DESIGNAR como Gerente Titular al Sr. Roberto Carlos Aguirre "
        "(DNI 20.345.678) y como Gerente Suplente a la Sra. María Elena Torres (DNI 27.111.456), "
        "por el término de TRES (3) ejercicios. Los designados aceptan el cargo y constituyen "
        "domicilio especial en la sede social.",
        "No habiendo más asuntos que tratar, se levanta la sesión siendo las 11:30 horas.",
    ],
    "Acta de designación de autoridades. Fecha 28/04/2024. Transcripta al Libro de Actas N° 2.",
)

# 4. CONSTANCIA AFIP — CUIT en filename
c = "30709876543"
build(
    f"{c}_constancia_inscripcion_afip.pdf",
    "CONSTANCIA DE INSCRIPCIÓN",
    "AFIP · Administración Federal de Ingresos Públicos",
    [
        kv_table([
            ["Apellido y Nombre / Denominación:", ENTIDADES[c]],
            ["CUIT:", fmt_cuit(c)],
            ["Fecha de emisión:", "12/01/2025"],
            ["Impuestos:", "IVA · Ganancias Sociedades · Empleador"],
            ["Actividad principal:", "492290 - Servicio de transporte automotor de cargas"],
            ["Domicilio fiscal:", "Av. Corrientes 3200, CABA"],
        ]),
        "La Administración Federal de Ingresos Públicos hace constar que el contribuyente "
        "referenciado se encuentra inscripto en los tributos indicados a la fecha de emisión "
        "de la presente constancia.",
        "Esta constancia tiene una validez de CIENTO OCHENTA (180) días corridos desde su emisión. "
        "Fecha de vencimiento: 11/07/2025.",
    ],
    "Constancia de inscripción AFIP generada el 12/01/2025. Documento de validez temporal.",
)

# 5. BALANCE / ESTADOS CONTABLES — CUIT en filename, vencimiento por regla
c = "33698765439"
build(
    f"{c}_estados_contables_2024.pdf",
    "ESTADOS CONTABLES",
    ENTIDADES[c],
    [
        kv_table([
            ["Razón social:", ENTIDADES[c]],
            ["CUIT:", fmt_cuit(c)],
            ["Ejercicio económico N°:", "12"],
            ["Fecha de cierre:", "31/12/2024"],
            ["Fecha de emisión del informe:", "15/03/2025"],
        ]),
        "Estados contables correspondientes al ejercicio económico finalizado el 31 de diciembre "
        "de 2024, presentados en forma comparativa con el ejercicio anterior, expresados en moneda "
        "homogénea conforme a las normas contables profesionales vigentes.",
        "<b>ESTADO DE SITUACIÓN PATRIMONIAL (resumen).</b> Activo total: $ 145.320.000. "
        "Pasivo total: $ 78.900.000. Patrimonio neto: $ 66.420.000.",
        "<b>ESTADO DE RESULTADOS (resumen).</b> Ventas netas: $ 312.500.000. Resultado del "
        "ejercicio (ganancia): $ 18.740.000.",
        "El presente informe del auditor fue emitido con opinión favorable sin salvedades.",
    ],
    "Estados contables ejercicio cerrado 31/12/2024. Nota: los balances se consideran vigentes por 12 meses desde el cierre.",
)

# 6. INFORME CREDITICIO NOSIS — CUIT en filename
c = "33698765439"
build(
    f"{c}_informe_nosis.pdf",
    "INFORME CREDITICIO",
    "NOSIS · Información Comercial",
    [
        kv_table([
            ["Razón social:", ENTIDADES[c]],
            ["CUIT:", fmt_cuit(c)],
            ["Fecha de consulta:", "20/02/2025"],
            ["Score Nosis:", "742 / 999 (riesgo bajo)"],
            ["Situación BCRA:", "Situación 1 - Normal"],
        ]),
        "El presente informe resume la situación crediticia y comercial de la entidad consultada "
        "según registros de la Central de Deudores del BCRA y fuentes públicas a la fecha de consulta.",
        "No se registran cheques rechazados en los últimos 24 meses. No se registran juicios "
        "comerciales ni concursos. Deuda financiera declarada dentro de parámetros normales para "
        "el segmento de actividad.",
    ],
    "Informe generado el 20/02/2025. Documento de referencia comercial, sin vencimiento formal.",
)

# 7. ESTATUTO de la 4ta entidad — CUIT SOLO en contenido (filename sin CUIT)
#    -> fuerza el match por CONTENIDO (nivel 3)
c = "30715558882"
build(
    "estatuto_consultora_2021.pdf",
    "ESTATUTO SOCIAL",
    ENTIDADES[c],
    [
        kv_table([
            ["Razón social:", ENTIDADES[c]],
            ["CUIT:", fmt_cuit(c)],
            ["Tipo societario:", "Sociedad por Acciones Simplificada (S.A.S.)"],
            ["Fecha de constitución:", "09/09/2021"],
        ]),
        "<b>ARTÍCULO PRIMERO.</b> Se constituye CONSULTORA RIVADAVIA S.A.S., con domicilio en la "
        "Ciudad Autónoma de Buenos Aires, bajo el régimen de la Ley 27.349 de Apoyo al Capital "
        "Emprendedor.",
        "<b>ARTÍCULO SEGUNDO — OBJETO.</b> Prestación de servicios de consultoría en gestión "
        "empresarial, tecnología de la información y transformación digital.",
        "<b>ARTÍCULO TERCERO — CAPITAL.</b> El capital social se fija en PESOS DOS MILLONES "
        "($2.000.000), dividido en acciones ordinarias.",
    ],
    "Estatuto S.A.S. constituido el 09/09/2021 vía plataforma TAD. Nombre de archivo sin CUIT (caso de match por contenido).",
)

# 8. PODER de la 4ta entidad — CUIT SOLO en contenido
c = "30715558882"
build(
    "poder_especial_bancario.pdf",
    "PODER ESPECIAL BANCARIO",
    ENTIDADES[c],
    [
        kv_table([
            ["Otorgante:", ENTIDADES[c]],
            ["CUIT otorgante:", fmt_cuit(c)],
            ["Apoderado:", "Lucía Fernández Rossi, DNI 30.998.221"],
            ["Fecha de otorgamiento:", "18/10/2024"],
            ["Vigencia hasta:", "18/10/2025"],
        ]),
        "CONSULTORA RIVADAVIA S.A.S. otorga poder especial a favor de la apoderada mencionada, "
        "limitado a la operatoria bancaria ante el banco depositario: apertura y cierre de cuentas, "
        "libramiento de cheques y constitución de plazos fijos.",
        "El presente poder especial vence el 18/10/2025.",
    ],
    "Poder especial. Fecha de emisión 18/10/2024. Nombre de archivo sin CUIT.",
)

# 9. DOCUMENTO DE IDENTIDAD — apoderado, sin CUIT de empresa -> cola de revisión
build(
    "dni_apoderado_escaneado.pdf",
    "DOCUMENTO NACIONAL DE IDENTIDAD",
    "República Argentina",
    [
        kv_table([
            ["Apellido:", "MÉNDEZ"],
            ["Nombre:", "JUAN ALBERTO"],
            ["DNI:", "24.876.123"],
            ["Fecha de nacimiento:", "03/07/1975"],
            ["Fecha de emisión:", "11/05/2019"],
            ["Vencimiento:", "11/05/2034"],
        ]),
        "Documento de identidad de persona física. No contiene CUIT de persona jurídica: la "
        "asociación a la entidad debe resolverse por contexto (apoderado de Estancias del Sur S.A.) "
        "o derivarse a la cola de revisión manual.",
    ],
    "DNI de persona física. Caso deliberado SIN CUIT de empresa -> debe caer en cola de revisión.",
)

# 10. CONTROL INTERNO / AML — genérico sin CUIT claro -> cola de revisión
build(
    "reporte_control_interno_kyc.pdf",
    "REPORTE DE CONTROLES INTERNOS · KYC / AML",
    "Área de Cumplimiento",
    [
        "Reporte de controles internos de prevención de lavado de activos y financiación del "
        "terrorismo (PLA/FT) correspondiente al proceso de alta de cliente.",
        "Se verificaron: identidad de los firmantes, matriz de riesgo del cliente, screening "
        "contra listas de sanciones (OFAC, ONU) y origen de fondos declarado. Resultado: "
        "aprobado con riesgo medio. Fecha del control: 03/02/2025.",
        "Nota: el documento no cita CUIT ni razón social de forma explícita; requiere resolución "
        "por contexto o revisión manual.",
    ],
    "Documento de compliance sin CUIT explícito. Caso de cola de revisión.",
)

print(f"\nListo. {len(os.listdir(OUT))} documentos en: {OUT}")
print("Resumen de casos de resolución de entidad:")
print("  - determinístico (CUIT en filename): docs 1-6")
print("  - por contenido (CUIT solo en texto): docs 7-8")
print("  - cola de revisión (sin CUIT):        docs 9-10")
