import re

from flask import Blueprint, abort, jsonify, render_template, request, send_file
from sqlalchemy import func

from app.extensions import db
from app.models.acta import Acta
from app.models.inventario import Inventario
from app.utils.auditoria import registrar
from app.utils.decorators import admin_o_editor_required, login_required, usuario_actual
from app.utils.pdf_acta import generar_acta_consolidada_pdf, generar_acta_pdf

acta_bp = Blueprint("acta", __name__)

ITEMS_POR_PAGINA_ACTAS = 20

# Campos del bien que se guardan en el snapshot inmutable de cada acta (los
# mismos que se muestran en la tabla del PDF consolidado). Es una copia de
# los VALORES en el momento de emisión, no una referencia al bien: si el bien
# cambia o se elimina después, reimprimir el acta debe seguir mostrando esto.
_CAMPOS_SNAPSHOT = [
    "codigo_bien", "codigo_anterior", "bien", "serie_identificacion", "modelo_caracteristicas",
    "marca_otros", "color", "material", "estado_bien", "ubicacion_bodega", "valor_compra",
]


def _bienes_de_custodio(custodio: str):
    """Coincidencia EXACTA de custodio (sin distinguir mayúsculas/tildes por la
    collation utf8mb4_unicode_ci), sin tratar el texto como patrón LIKE: si el
    nombre del custodio contiene '%' o '_' (poco común pero posible en datos
    de Excel), no deben interpretarse como comodines.
    """
    return (
        Inventario.query.filter(
            func.lower(Inventario.custodio_actual) == custodio.lower(),
            Inventario.eliminado.is_(False),
        )
        .order_by(Inventario.codigo_bien)
        .all()
    )


def _serializar_bien_para_snapshot(bien: Inventario) -> dict:
    datos = {}
    for campo in _CAMPOS_SNAPSHOT:
        valor = getattr(bien, campo)
        # Decimal no es serializable a JSON directamente.
        datos[campo] = float(valor) if campo == "valor_compra" and valor is not None else valor
    return datos


@acta_bp.route("/descargar_acta_pdf/<codigo>", methods=["GET"])
@login_required
def descargar(codigo):
    bien = Inventario.query.filter_by(codigo_bien=codigo, eliminado=False).first_or_404()
    buffer = generar_acta_pdf(bien)

    registrar(usuario=usuario_actual().username, accion="Descarga de acta", codigo_bien=codigo,
              detalle="Acta de custodia PDF descargada")

    nombre_archivo = f"acta_custodia_{codigo}.pdf"
    return send_file(buffer, as_attachment=True, download_name=nombre_archivo, mimetype="application/pdf")


@acta_bp.route("/custodios/buscar", methods=["GET"])
@admin_o_editor_required
def custodios_buscar():
    """Nombres de custodio (distintos) que coinciden con el término, para el
    autocompletado del modal "Crear Actas"."""
    termino = (request.args.get("q") or "").strip()
    if not termino:
        return jsonify([])

    patron = f"%{termino}%"
    filas = (
        Inventario.query.with_entities(Inventario.custodio_actual)
        .filter(Inventario.custodio_actual.ilike(patron), Inventario.eliminado.is_(False))
        .distinct()
        .order_by(Inventario.custodio_actual)
        .limit(15)
        .all()
    )
    return jsonify([fila[0] for fila in filas if fila[0]])


@acta_bp.route("/custodios/bienes", methods=["GET"])
@admin_o_editor_required
def custodios_bienes():
    """Bienes de un custodio (coincidencia exacta, sin distinguir mayúsculas),
    para la vista previa del modal "Crear Actas" antes de generar el PDF."""
    custodio = (request.args.get("custodio") or "").strip()
    if not custodio:
        return jsonify({"bienes": [], "total_valor": 0})

    bienes = _bienes_de_custodio(custodio)
    total_valor = sum(float(b.valor_compra) for b in bienes if b.valor_compra is not None)

    return jsonify({
        "bienes": [
            {
                "codigo_bien": b.codigo_bien,
                "bien": b.bien,
                "estado_bien": b.estado_bien,
                "valor_compra": float(b.valor_compra) if b.valor_compra is not None else None,
            }
            for b in bienes
        ],
        "total_valor": total_valor,
    })


def _nombre_archivo_acta(custodio: str, nro_acta: int) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", custodio).strip("_") or "custodio"
    return f"acta_custodia_{nro_acta:06d}_{slug}.pdf"


@acta_bp.route("/custodios/vista_previa_pdf", methods=["GET"])
@admin_o_editor_required
def vista_previa_consolidado():
    """PDF de vista previa: NO registra fila en `actas` ni consume un número
    correlativo. Se usa solo para que el modal muestre cómo va a quedar el
    acta antes de que el usuario decida emitirla de verdad (con
    /descargar_actas_pdf, que sí persiste y numera). Por eso se llama sin
    nro_acta y se sirve inline (no como adjunto), para incrustarla en un
    <iframe> vía blob URL.
    """
    custodio = (request.args.get("custodio") or "").strip()
    if not custodio:
        abort(404)

    bienes = _bienes_de_custodio(custodio)
    if not bienes:
        abort(404)

    usuario = usuario_actual()
    nombre_elabora = usuario.nombre_completo or usuario.username
    snapshot = [_serializar_bien_para_snapshot(b) for b in bienes]

    buffer = generar_acta_consolidada_pdf(
        snapshot, custodio, nombre_elabora, direccion_elabora=getattr(usuario, "direccion", None),
    )
    return send_file(buffer, as_attachment=False, mimetype="application/pdf")


@acta_bp.route("/descargar_actas_pdf", methods=["GET"])
@admin_o_editor_required
def descargar_consolidado():
    custodio = (request.args.get("custodio") or "").strip()
    if not custodio:
        abort(404)

    bienes = _bienes_de_custodio(custodio)
    if not bienes:
        abort(404)

    usuario = usuario_actual()
    nombre_elabora = usuario.nombre_completo or usuario.username
    snapshot = [_serializar_bien_para_snapshot(b) for b in bienes]
    total_valor = sum(b["valor_compra"] for b in snapshot if b["valor_compra"] is not None)

    # El acta se registra ANTES de generar el PDF: el número correlativo
    # (el id de esta fila) y la fecha de emisión que se imprimen en el PDF
    # deben ser los mismos que quedan guardados para la reimpresión futura,
    # no un timestamp calculado aparte que podría desincronizarse.
    acta = Acta(
        custodio=custodio, usuario_elabora=usuario.username, elaborado_nombre=nombre_elabora,
        elaborado_direccion=getattr(usuario, "direccion", None), total_bienes=len(snapshot),
        total_valor=total_valor, bienes_snapshot=snapshot,
    )
    db.session.add(acta)
    db.session.commit()

    buffer = generar_acta_consolidada_pdf(
        snapshot, custodio, nombre_elabora, direccion_elabora=acta.elaborado_direccion,
        nro_acta=acta.nro_acta, fecha_emision=acta.fecha_emision.date(),
    )

    registrar(usuario=usuario.username, accion="Emisión de acta consolidada", detalle=(
        f"Acta Nro. {acta.nro_acta} emitida para el custodio '{custodio}' ({len(bienes)} bienes)"
    ))

    nombre_archivo = _nombre_archivo_acta(custodio, acta.nro_acta)
    return send_file(buffer, as_attachment=True, download_name=nombre_archivo, mimetype="application/pdf")


@acta_bp.route("/actas", methods=["GET"])
@admin_o_editor_required
def historial():
    """Historial de actas emitidas, para poder reimprimirlas sin regenerar
    nada desde el inventario actual (usa el snapshot guardado en cada fila)."""
    termino = (request.args.get("custodio") or "").strip()
    pagina = request.args.get("pagina", 1, type=int)

    consulta = Acta.query
    if termino:
        consulta = consulta.filter(Acta.custodio.ilike(f"%{termino}%"))
    consulta = consulta.order_by(Acta.id.desc())

    total = consulta.count()
    total_paginas = max(1, (total + ITEMS_POR_PAGINA_ACTAS - 1) // ITEMS_POR_PAGINA_ACTAS)
    pagina = min(max(1, pagina), total_paginas)
    actas = consulta.offset((pagina - 1) * ITEMS_POR_PAGINA_ACTAS).limit(ITEMS_POR_PAGINA_ACTAS).all()

    return render_template(
        "actas_historial.html", actas=actas, termino=termino,
        pagina=pagina, total_paginas=total_paginas, total=total,
    )


@acta_bp.route("/actas/<int:acta_id>/descargar", methods=["GET"])
@admin_o_editor_required
def reimprimir(acta_id):
    """Reimprime una acta ya emitida a partir de su snapshot guardado: nunca
    vuelve a consultar `inventario`, así que el PDF es idéntico al original
    aunque los bienes hayan cambiado de estado/valor o se hayan eliminado
    desde entonces."""
    acta = Acta.query.get_or_404(acta_id)
    usuario = usuario_actual()

    buffer = generar_acta_consolidada_pdf(
        acta.bienes_snapshot, acta.custodio, acta.elaborado_nombre or acta.usuario_elabora,
        direccion_elabora=acta.elaborado_direccion, nro_acta=acta.nro_acta,
        fecha_emision=acta.fecha_emision.date(),
    )

    registrar(usuario=usuario.username, accion="Reimpresión de acta consolidada",
              detalle=f"Acta Nro. {acta.nro_acta} (custodio '{acta.custodio}') reimpresa desde el historial")

    nombre_archivo = _nombre_archivo_acta(acta.custodio, acta.nro_acta)
    return send_file(buffer, as_attachment=True, download_name=nombre_archivo, mimetype="application/pdf")
