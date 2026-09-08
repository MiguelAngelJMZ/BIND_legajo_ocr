#!/usr/bin/env python3
"""
Generador de documentos de DEMO para el POC Legajo Lakehouse.

SET 1 → demo/renovaciones/  (3 PDFs para subir al portal del cliente y probar el circuito de aprobación)
SET 2 → demo/nuevos_docs/   (5 PDFs para ingestar al Volume y mostrar el pipeline en vivo)

Ejecutar: python3 generar_demo.py
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

BASE    = os.path.dirname(__file__)
SET1    = os.path.join(BASE, "demo", "renovaciones")
SET2    = os.path.join(BASE, "demo", "nuevos_docs")
os.makedirs(SET1, exist_ok=True)
os.makedirs(SET2, exist_ok=True)

ENTIDADES = {
    "30712345678": "Estancias del Sur S.A.",
    "30709876543": "Logística Andina S.R.L.",
    "33698765439": "Grupo Textil Paraná S.A.",
    "30715558882": "Consultora Rivadavia S.A.S.",
}

styles = getSampleStyleSheet()
H    = ParagraphStyle("H",    parent=styles["Title"],    fontSize=15, spaceAfter=14, textColor=colors.HexColor("#1B3139"))
SUB  = ParagraphStyle("SUB",  parent=styles["Heading2"], fontSize=11, textColor=colors.HexColor("#C4260F"))
BODY = ParagraphStyle("BODY", parent=styles["BodyText"], fontSize=10, leading=15, alignment=4)
SMALL= ParagraphStyle("SMALL",parent=styles["BodyText"], fontSize=8,  textColor=colors.grey)


def fmt_cuit(c):
    return f"{c[:2]}-{c[2:10]}-{c[10:]}"


def kv_table(rows):
    t = Table(rows, colWidths=[5*cm, 9*cm])
    t.setStyle(TableStyle([
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",    (0, 0), (0,  -1), colors.HexColor("#1B3139")),
        ("FONTNAME",     (0, 0), (0,  -1), "Helvetica-Bold"),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LINEBELOW",    (0, 0), (-1, -1), 0.4, colors.HexColor("#DAD5CD")),
    ]))
    return t


def build(folder, filename, title, subtitle, paragraphs, footer):
    path = os.path.join(folder, filename)
    doc  = SimpleDocTemplate(path, pagesize=A4,
                             topMargin=2.2*cm, bottomMargin=2*cm,
                             leftMargin=2.5*cm, rightMargin=2.5*cm)
    story = [Paragraph(title, H), Paragraph(subtitle, SUB), Spacer(1, 14)]
    for p in paragraphs:
        story.append(p if isinstance(p, Table) else Paragraph(p, BODY))
        story.append(Spacer(1, 8))
    story += [Spacer(1, 20), Paragraph(footer, SMALL)]
    doc.build(story)
    print(f"  ✓ {filename}")


# =============================================================================
# SET 1 · RENOVACIONES  (fechas futuras → el sistema los clasifica como vigente)
# =============================================================================
print("\n── SET 1: renovaciones ──")

# 1a. Constancia AFIP renovada — Logística Andina
c = "30709876543"
build(SET1, f"{c}_constancia_inscripcion_renovada.pdf",
      "CONSTANCIA DE INSCRIPCIÓN — RENOVACIÓN",
      "AFIP · Administración Federal de Ingresos Públicos",
      [
          kv_table([
              ["Apellido y Nombre / Denominación:", ENTIDADES[c]],
              ["CUIT:", fmt_cuit(c)],
              ["Fecha de emisión:", "07/09/2026"],
              ["Impuestos:", "IVA · Ganancias Sociedades · Empleador"],
              ["Actividad principal:", "492290 - Servicio de transporte automotor de cargas"],
              ["Domicilio fiscal:", "Av. Corrientes 3200, CABA"],
              ["Fecha de vencimiento:", "06/03/2028"],
          ]),
          "La Administración Federal de Ingresos Públicos hace constar que el contribuyente "
          "referenciado se encuentra inscripto en los tributos indicados a la fecha de emisión "
          "de la presente constancia.",
          "Esta constancia tiene una validez de DIECIOCHO (18) meses corridos desde su emisión. "
          "Fecha de vencimiento: 06/03/2028.",
      ],
      "Constancia de inscripción AFIP generada el 07/09/2026. Renovación — vence 06/03/2028.")

# 1b. Poder especial renovado — Consultora Rivadavia
c = "30715558882"
build(SET1, f"{c}_poder_especial_renovado.pdf",
      "PODER ESPECIAL BANCARIO — RENOVACIÓN",
      ENTIDADES[c],
      [
          kv_table([
              ["Otorgante:", ENTIDADES[c]],
              ["CUIT otorgante:", fmt_cuit(c)],
              ["Apoderada:", "Lucía Fernández Rossi, DNI 30.998.221"],
              ["Fecha de otorgamiento:", "07/09/2026"],
              ["Vigencia hasta:", "07/09/2029"],
          ]),
          "CONSULTORA RIVADAVIA S.A.S. otorga poder especial a favor de la apoderada mencionada, "
          "limitado a la operatoria bancaria ante el banco depositario: apertura y cierre de cuentas, "
          "libramiento de cheques y constitución de plazos fijos.",
          "El presente poder especial vence el 07/09/2029.",
      ],
      "Poder especial renovado. Fecha de emisión 07/09/2026. Vigente hasta 07/09/2029.")

# 1c. Poder general renovado — Estancias del Sur
c = "30712345678"
build(SET1, f"{c}_poder_general_renovado.pdf",
      "PODER GENERAL AMPLIO — RENOVACIÓN",
      ENTIDADES[c],
      [
          kv_table([
              ["Otorgante:", ENTIDADES[c]],
              ["CUIT otorgante:", fmt_cuit(c)],
              ["Apoderado:", "Juan Alberto Méndez, DNI 24.876.123"],
              ["Fecha de otorgamiento:", "07/09/2026"],
              ["Vigencia hasta:", "15/01/2030"],
          ]),
          "En la Ciudad de Buenos Aires, a los siete días del mes de septiembre de 2026, comparece "
          "el representante legal de ESTANCIAS DEL SUR S.A. y CONFIERE PODER GENERAL AMPLIO a favor "
          "del señor Juan Alberto Méndez para que en nombre y representación de la sociedad ejerza "
          "las siguientes facultades:",
          "<b>a)</b> Representar a la sociedad ante organismos nacionales, provinciales y municipales, "
          "AFIP, ARCA, IGJ, ANSES y entidades bancarias. <b>b)</b> Operar cuentas corrientes y "
          "cajas de ahorro, librar y endosar cheques. <b>c)</b> Celebrar contratos de compraventa, "
          "locación y mutuo.",
          "El presente poder tendrá una vigencia hasta el 15/01/2030.",
      ],
      "Poder general renovado. Escritura N° 520, Registro Notarial 12 CABA. Emisión 07/09/2026.")


# =============================================================================
# SET 2 · NUEVOS DOCUMENTOS  (para demo del pipeline — distintos estados)
# =============================================================================
print("\n── SET 2: nuevos_docs ──")

# 2a. Acta de designación 2026 — Estancias del Sur → vigente (sin vencimiento formal)
c = "30712345678"
build(SET2, f"{c}_acta_designacion_2026.pdf",
      "ACTA DE ASAMBLEA GENERAL ORDINARIA",
      ENTIDADES[c],
      [
          kv_table([
              ["Razón social:", ENTIDADES[c]],
              ["CUIT:", fmt_cuit(c)],
              ["Tipo de asamblea:", "General Ordinaria"],
              ["Fecha de celebración:", "01/08/2026"],
              ["Acta N°:", "15"],
          ]),
          "En la sede social de ESTANCIAS DEL SUR S.A., siendo las 10:00 horas del día 01 de agosto "
          "de 2026, se reúnen los accionistas que representan el 100% del capital social a fin de "
          "tratar el siguiente orden del día: renovación de autoridades y ratificación de poderes.",
          "Se resuelve por unanimidad DESIGNAR como Presidente al Sr. Carlos Eduardo Peralta "
          "(DNI 18.234.567) y como Director Suplente a la Sra. Patricia Montoya (DNI 31.456.789), "
          "por el término de TRES (3) ejercicios.",
          "No habiendo más asuntos que tratar, se levanta la sesión siendo las 11:30 horas.",
      ],
      "Acta N° 15. Fecha 01/08/2026. Documento sin vencimiento explícito → estado: vigente.")

# 2b. Estados contables 2025 — Logística Andina → vigente (vence 20/03/2027 por regla)
c = "30709876543"
build(SET2, f"{c}_estados_contables_2025.pdf",
      "ESTADOS CONTABLES",
      ENTIDADES[c],
      [
          kv_table([
              ["Razón social:", ENTIDADES[c]],
              ["CUIT:", fmt_cuit(c)],
              ["Ejercicio económico N°:", "8"],
              ["Fecha de cierre:", "31/12/2025"],
              ["Fecha de emisión del informe:", "20/03/2026"],
          ]),
          "Estados contables correspondientes al ejercicio económico finalizado el 31 de diciembre "
          "de 2025, presentados en forma comparativa con el ejercicio anterior, expresados en moneda "
          "homogénea conforme a las normas contables profesionales vigentes.",
          "<b>ESTADO DE SITUACIÓN PATRIMONIAL (resumen).</b> Activo total: $ 98.750.000. "
          "Pasivo total: $ 41.200.000. Patrimonio neto: $ 57.550.000.",
          "<b>ESTADO DE RESULTADOS (resumen).</b> Ventas netas: $ 215.300.000. Resultado del "
          "ejercicio (ganancia): $ 12.480.000.",
          "El presente informe del auditor fue emitido con opinión favorable sin salvedades.",
      ],
      "Estados contables ejercicio cerrado 31/12/2025. Regla: vence 12 meses desde la emisión → 20/03/2027 → vigente.")

# 2c. Constancia AFIP 2026 — Grupo Textil Paraná → por_vencer en ~6 meses
c = "33698765439"
build(SET2, f"{c}_constancia_afip_2026.pdf",
      "CONSTANCIA DE INSCRIPCIÓN",
      "AFIP · Administración Federal de Ingresos Públicos",
      [
          kv_table([
              ["Apellido y Nombre / Denominación:", ENTIDADES[c]],
              ["CUIT:", fmt_cuit(c)],
              ["Fecha de emisión:", "11/09/2026"],
              ["Impuestos:", "IVA · Ganancias Sociedades · Empleador · IIBB"],
              ["Actividad principal:", "131900 - Fabricación de productos textiles"],
              ["Domicilio fiscal:", "Ruta Nacional 11, km 482, Santa Fe"],
              ["Fecha de vencimiento:", "10/03/2027"],
          ]),
          "La AFIP hace constar que el contribuyente referenciado se encuentra inscripto en los "
          "tributos indicados a la fecha de emisión de la presente constancia.",
          "Esta constancia tiene una validez de CIENTO OCHENTA (180) días corridos desde su emisión. "
          "Fecha de vencimiento: 10/03/2027.",
      ],
      "Constancia AFIP generada el 11/09/2026. Vence 10/03/2027 (180 días) → por_vencer en ~6 meses.")

# 2d. Estatuto actualizado — Consultora Rivadavia — CUIT SOLO en contenido → match nivel 3
c = "30715558882"
build(SET2, "estatuto_rivadavia_actualizado.pdf",
      "ESTATUTO SOCIAL — TEXTO ORDENADO 2026",
      ENTIDADES[c],
      [
          kv_table([
              ["Razón social:", ENTIDADES[c]],
              ["CUIT:", fmt_cuit(c)],
              ["Tipo societario:", "Sociedad por Acciones Simplificada (S.A.S.)"],
              ["Fecha de constitución:", "09/09/2021"],
              ["Última modificación:", "02/09/2026"],
          ]),
          "<b>ARTÍCULO PRIMERO.</b> Se constituye CONSULTORA RIVADAVIA S.A.S., con domicilio en la "
          "Ciudad Autónoma de Buenos Aires, bajo el régimen de la Ley 27.349 de Apoyo al Capital "
          "Emprendedor.",
          "<b>ARTÍCULO SEGUNDO — OBJETO.</b> Prestación de servicios de consultoría en gestión "
          "empresarial, tecnología de la información y transformación digital. Se incorpora: "
          "desarrollo de soluciones de inteligencia artificial y análisis de datos.",
          "<b>ARTÍCULO TERCERO — CAPITAL.</b> El capital social se eleva a PESOS DIEZ MILLONES "
          "($10.000.000), dividido en acciones ordinarias. Ampliación aprobada el 02/09/2026.",
      ],
      "Texto ordenado 2026. Nombre de archivo SIN CUIT → resolución por contenido (nivel 3).")

# 2e. Dictamen de cumplimiento — sin CUIT → cola de revisión
build(SET2, "dictamen_cumplimiento_regulatorio.pdf",
      "DICTAMEN DE CUMPLIMIENTO REGULATORIO",
      "Área de Auditoría Interna",
      [
          "Dictamen emitido por el área de Auditoría Interna en el marco del proceso de revisión "
          "anual de cumplimiento normativo (compliance) para el ejercicio 2026.",
          "Se auditaron los siguientes aspectos: estructura societaria, vigencia de poderes, "
          "cumplimiento de obligaciones tributarias, situación ante BCRA, y adecuación a la "
          "Resolución UIF 30/2017 de Prevención de Lavado de Activos.",
          "Resultado: APTO. No se detectaron observaciones materiales. Se recomienda renovar "
          "la constancia de inscripción AFIP antes del próximo vencimiento.",
          "Nota: el presente dictamen es un documento de uso interno y no identifica la entidad "
          "evaluada de forma explícita en el cuerpo del texto.",
      ],
      "Dictamen interno. Sin CUIT ni razón social explícita → cola de revisión (nivel 4).")


# =============================================================================
# RESUMEN
# =============================================================================
print(f"""
{'='*62}
RESUMEN DE DOCUMENTOS GENERADOS
{'='*62}

SET 1 · demo/renovaciones/  (subir al portal del cliente en la app)
  30709876543_constancia_inscripcion_renovada.pdf
    └─ estado esperado post-aprobación: vigente (vence 06/03/2028)
  30715558882_poder_especial_renovado.pdf
    └─ estado esperado post-aprobación: vigente (vence 07/09/2029)
  30712345678_poder_general_renovado.pdf
    └─ estado esperado post-aprobación: vigente (vence 15/01/2030)

SET 2 · demo/nuevos_docs/  (ingestar al Volume, mostrar pipeline)
  30712345678_acta_designacion_2026.pdf
    └─ estado: vigente  (sin vencimiento formal)
  30709876543_estados_contables_2025.pdf
    └─ estado: vigente  (vence 20/03/2027 por regla 12 meses)
  33698765439_constancia_afip_2026.pdf
    └─ estado: por_vencer  (vence 10/03/2027, <6 meses)
  estatuto_rivadavia_actualizado.pdf
    └─ match: por contenido (nivel 3) — filename sin CUIT
  dictamen_cumplimiento_regulatorio.pdf
    └─ destino: cola_revision  (sin CUIT en ningún lado)
{'='*62}
""")
