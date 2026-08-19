"""Generación del acta de custodia en PDF (reportlab) con código QR (qrcode)
para verificación rápida del bien.
"""
import io
import os
from datetime import date
from xml.sax.saxutils import escape as _escape_xml

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import cm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "img", "login_img.png")


class _ImagenDesplazada(Image):
    """Igual que `Image`, pero dibujada con un corrimiento (dx, dy) en puntos
    respecto a su posición normal. El espacio reservado en la tabla (wrap())
    no cambia, así que el desplazamiento no afecta el centrado de las demás
    celdas: la imagen simplemente se dibuja corrida dentro/fuera de su celda.
    """

    def __init__(self, path, width, height, dx=0, dy=0):
        super().__init__(path, width=width, height=height)
        self._dx = dx
        self._dy = dy

    def draw(self):
        self.canv.saveState()
        self.canv.translate(self._dx, self._dy)
        super().draw()
        self.canv.restoreState()


def _valor(v) -> str:
    if v is None:
        return "-"
    return str(v)


def generar_qr(bien) -> io.BytesIO:
    contenido = (
        f"Código: {_valor(bien.codigo_bien)}\n"
        f"Bien: {_valor(bien.bien)}\n"
        f"Serie: {_valor(bien.serie_identificacion)}\n"
        f"Custodio: {_valor(bien.custodio_actual)}\n"
        f"Estado: {_valor(bien.estado_bien)}"
    )
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(contenido)
    qr.make(fit=True)
    imagen = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def generar_acta_pdf(bien) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
    )
    estilos = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        "TituloInstitucional", parent=estilos["Heading1"], textColor=colors.HexColor("#2c3e50"),
        alignment=1, fontSize=16,
    )
    subtitulo_style = ParagraphStyle(
        "Subtitulo", parent=estilos["Normal"], alignment=1, textColor=colors.HexColor("#555555"),
    )

    elementos = [
        Paragraph("INAMHI | Control de Activos", titulo_style),
        Paragraph("Acta de Custodia de Bien", subtitulo_style),
        Spacer(1, 1 * cm),
    ]

    datos = [
        ["Código del Bien", _valor(bien.codigo_bien)],
        ["Categoría / Item", _valor(bien.item_renglon)],
        ["Nombre del Bien", _valor(bien.bien)],
        ["Estado del Bien", _valor(bien.estado_bien)],
        ["Serie / Identificación", _valor(bien.serie_identificacion)],
        ["Modelo / Características", _valor(bien.modelo_caracteristicas)],
        ["Marca / Otros", _valor(bien.marca_otros)],
        ["Custodio Actual", _valor(bien.custodio_actual)],
        ["Ubicación de Bodega", _valor(bien.ubicacion_bodega)],
        ["Valor de Compra", _valor(bien.valor_compra)],
        ["Estado de Revisión", _valor(bien.estado)],
    ]
    tabla = Table(datos, colWidths=[6 * cm, 9 * cm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, colors.HexColor("#f4f6f7")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 1 * cm))

    qr_buffer = generar_qr(bien)
    elementos.append(Paragraph("Código QR de verificación:", estilos["Heading4"]))
    elementos.append(Image(qr_buffer, width=3.5 * cm, height=3.5 * cm))

    doc.build(elementos)
    buffer.seek(0)
    return buffer


def _celda(texto, estilo) -> Paragraph:
    return Paragraph(_escape_xml(_valor(texto)), estilo)


def generar_acta_consolidada_pdf(
    bienes: list[dict], custodio: str, nombre_elabora: str, direccion_elabora: str | None = None,
    nro_acta: int | None = None, fecha_emision: date | None = None,
) -> io.BytesIO:
    """Acta de custodia consolidada: todos los bienes de un custodio en un
    solo PDF (tabla en formato apaisado + firmas), en vez de una descarga
    individual por bien.

    `bienes` es una lista de DICTS (no objetos `Inventario`), a propósito:
    así la misma función sirve tanto para la emisión original (dicts armados
    desde `Inventario` en el momento) como para la reimpresión desde
    `Acta.bienes_snapshot` (dicts que vienen directo de la base, ya
    guardados), sin acoplar este módulo al ORM ni a un modelo específico.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(letter),
        topMargin=1.2 * cm, bottomMargin=1.2 * cm, leftMargin=1.2 * cm, rightMargin=1.2 * cm,
    )
    estilos = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        "TituloConsolidado", parent=estilos["Heading2"], textColor=colors.HexColor("#2c3e50"),
        alignment=1, fontSize=15, spaceAfter=2,
    )
    subtitulo_style = ParagraphStyle(
        "SubtituloConsolidado", parent=estilos["Normal"], alignment=1,
        textColor=colors.HexColor("#555555"), fontSize=11,
    )
    celda_style = ParagraphStyle("Celda", parent=estilos["Normal"], fontSize=7, leading=8.5)
    celda_header_style = ParagraphStyle(
        "CeldaHeader", parent=estilos["Normal"], fontSize=7.5, leading=9,
        textColor=colors.white, fontName="Helvetica-Bold", alignment=1,
    )
    firma_rol_style = ParagraphStyle(
        "FirmaRol", parent=estilos["Normal"], alignment=1, fontSize=9, fontName="Helvetica-Bold",
    )
    firma_style = ParagraphStyle("Firma", parent=estilos["Normal"], alignment=1, fontSize=8.5, leading=11)

    elementos = []

    titulo_bloque = [
        Paragraph("INSTITUTO NACIONAL DE METEOROLOGÍA E HIDROLOGÍA - INAMHI", titulo_style),
        Paragraph("Acta de Constatación y Custodia de Bienes", subtitulo_style),
    ]
    if os.path.exists(LOGO_PATH):
        # Columna izquierda "fantasma" del mismo ancho que la del logo, para que
        # el título quede realmente centrado en la página y el logo a la derecha.
        ancho_logo_base = 3.4 * cm
        alto_logo_base = 1.78 * cm
        ancho_logo_col = 3.6 * cm
        logo = _ImagenDesplazada(
            LOGO_PATH,
            width=ancho_logo_base * 1.10,  # 10% más grande
            height=alto_logo_base * 1.10,
            dx=ancho_logo_base * 0.10,  # 10% hacia la derecha
            dy=alto_logo_base * 0.20,  # 20% hacia arriba
        )
        encabezado = Table(
            [["", titulo_bloque, logo]],
            colWidths=[ancho_logo_col, None, ancho_logo_col],
        )
        encabezado.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (2, 0), (2, 0), "CENTER"),
        ]))
        elementos.append(encabezado)
    else:
        elementos.extend(titulo_bloque)
    elementos.append(Spacer(1, 0.5 * cm))

    info_data = [
        ["Elaborado por:", nombre_elabora],
        ["Custodio:", custodio],
        ["Fecha:", (fecha_emision or date.today()).strftime("%d/%m/%Y")],
        ["Total de bienes:", str(len(bienes))],
    ]
    if nro_acta is not None:
        info_data.insert(0, ["Nro. Acta:", str(nro_acta)])
    info_tabla = Table(info_data, colWidths=[3.4 * cm, 8 * cm])
    info_tabla.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f4f6f7")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elementos.append(info_tabla)
    elementos.append(Spacer(1, 0.5 * cm))

    encabezados = ["Nro", "Código del Bien", "Código Anterior", "Bien", "Serie", "Modelo",
                   "Marca", "Color", "Material", "Estado", "Ubicación", "Valor"]
    filas = [[Paragraph(h, celda_header_style) for h in encabezados]]

    total_valor = 0.0
    for i, bien in enumerate(bienes, start=1):
        valor_crudo = bien.get("valor_compra")
        valor = float(valor_crudo) if valor_crudo is not None else 0.0
        total_valor += valor
        filas.append([
            Paragraph(str(i), celda_style),
            _celda(bien.get("codigo_bien"), celda_style),
            _celda(bien.get("codigo_anterior"), celda_style),
            _celda(bien.get("bien"), celda_style),
            _celda(bien.get("serie_identificacion"), celda_style),
            _celda(bien.get("modelo_caracteristicas"), celda_style),
            _celda(bien.get("marca_otros"), celda_style),
            _celda(bien.get("color"), celda_style),
            _celda(bien.get("material"), celda_style),
            _celda(bien.get("estado_bien"), celda_style),
            _celda(bien.get("ubicacion_bodega"), celda_style),
            Paragraph(f"$ {valor:,.2f}", celda_style),
        ])
    filas.append(["", "", "", "", "", "", "", "", "", "", "Total general", f"$ {total_valor:,.2f}"])

    anchos = [1.1 * cm, 2.7 * cm, 2.3 * cm, 3.8 * cm, 2.3 * cm, 2.7 * cm,
              1.9 * cm, 1.6 * cm, 1.8 * cm, 1.9 * cm, 3.2 * cm, 2 * cm]
    tabla = Table(filas, colWidths=anchos, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f4f6f7")]),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
        ("SPAN", (0, -1), (-2, -1)),
        ("ALIGN", (0, -1), (-2, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 9),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#eaf2ff")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elementos.append(tabla)

    firma_izquierda = [
        Paragraph("_____________________________", firma_style),
        Paragraph("ELABORADO POR / USUARIO FINAL", firma_rol_style),
        Paragraph(_escape_xml(nombre_elabora), firma_style),
        Paragraph(_escape_xml(direccion_elabora or "-"), firma_style),
    ]
    firma_derecha = [
        Paragraph("_____________________________", firma_style),
        Paragraph("VERIFICA / CUSTODIO FINAL", firma_rol_style),
        Paragraph(_escape_xml(custodio), firma_style),
        Paragraph("DIRECCIÓN ADMINISTRATIVA FINANCIERA", firma_style),
    ]
    tabla_firmas = Table([[firma_izquierda, firma_derecha]], colWidths=[12.7 * cm, 12.7 * cm])
    tabla_firmas.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    # KeepTogether evita que el espaciador y la tabla de firmas se separen en
    # páginas distintas (el espaciador solo cabría al final de una página,
    # dejando las firmas huérfanas al inicio de la siguiente).
    elementos.append(KeepTogether([Spacer(1, 3.9 * cm), tabla_firmas]))

    doc.build(elementos)
    buffer.seek(0)
    return buffer
