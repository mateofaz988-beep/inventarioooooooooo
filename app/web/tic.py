from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import or_

from app.extensions import db
from app.models.inventario import ESTADO_APROBADO, ESTADO_BORRADOR, ESTADO_EN_REVISION, ESTADO_OBSERVADO, Inventario
from app.utils.auditoria import registrar
from app.utils.busqueda import aplicar_busqueda_texto
from app.utils.decorators import admin_o_editor_required, usuario_actual

tic_bp = Blueprint("tic", __name__)

ESTADOS_FILTRO = {ESTADO_EN_REVISION, ESTADO_OBSERVADO, ESTADO_APROBADO}
ITEMS_POR_PAGINA = 15


@tic_bp.route("/tic/bandeja", methods=["GET"])
@admin_o_editor_required
def bandeja():
    termino = (request.args.get("q") or "").strip()
    estado_filtro = (request.args.get("estado") or "").strip()
    pagina = request.args.get("pagina", 1, type=int)

    base = Inventario.query.filter(Inventario.eliminado.is_(False))

    pendientes = base.filter(
        or_(Inventario.estado == ESTADO_EN_REVISION, Inventario.estado == ESTADO_BORRADOR, Inventario.estado.is_(None))
    ).count()
    observados = base.filter_by(estado=ESTADO_OBSERVADO).count()
    aprobados = base.filter_by(estado=ESTADO_APROBADO).count()
    total = base.count()

    consulta = base
    if estado_filtro and estado_filtro in ESTADOS_FILTRO:
        consulta = consulta.filter_by(estado=estado_filtro)
    elif estado_filtro not in ("", "TODOS"):
        estado_filtro = ""

    if termino:
        consulta = aplicar_busqueda_texto(consulta, termino)

    consulta = consulta.order_by(Inventario.id.desc())
    total_filtrado = consulta.count()
    total_paginas = max(1, (total_filtrado + ITEMS_POR_PAGINA - 1) // ITEMS_POR_PAGINA)
    pagina = min(max(1, pagina), total_paginas)

    bienes = consulta.offset((pagina - 1) * ITEMS_POR_PAGINA).limit(ITEMS_POR_PAGINA).all()

    return render_template(
        "bandeja_tic.html",
        bienes=bienes,
        kpi_pendientes=pendientes,
        kpi_observados=observados,
        kpi_aprobados=aprobados,
        kpi_total=total,
        termino=termino,
        estado_filtro=estado_filtro,
        pagina=pagina,
        total_paginas=total_paginas,
        total_filtrado=total_filtrado,
    )


@tic_bp.route("/tic/aprobar/<codigo>", methods=["POST"])
@admin_o_editor_required
def aprobar(codigo):
    usuario = usuario_actual()
    bien = Inventario.query.filter_by(codigo_bien=codigo, eliminado=False).first_or_404()
    nota = (request.form.get("nota") or "").strip()

    bien.estado = ESTADO_APROBADO
    bien.observaciones_tic = None
    bien.revisado_por_tic = usuario.username
    bien.fecha_revision_tic = datetime.utcnow()
    db.session.commit()

    registrar(usuario=usuario.username, accion="Aprobación de bien", codigo_bien=codigo,
              detalle=nota or "Bien aprobado sin observaciones adicionales")

    flash(f"Bien '{codigo}' aprobado correctamente.", "success")
    return redirect(url_for("tic.bandeja"))


@tic_bp.route("/tic/observar/<codigo>", methods=["POST"])
@admin_o_editor_required
def observar(codigo):
    usuario = usuario_actual()
    bien = Inventario.query.filter_by(codigo_bien=codigo, eliminado=False).first_or_404()
    motivo = (request.form.get("motivo") or "").strip()

    if not motivo:
        flash("Debes indicar un motivo para observar el bien.", "danger")
        return redirect(url_for("tic.bandeja"))

    bien.estado = ESTADO_OBSERVADO
    bien.observaciones_tic = motivo
    bien.revisado_por_tic = usuario.username
    bien.fecha_revision_tic = datetime.utcnow()
    db.session.commit()

    registrar(usuario=usuario.username, accion="Observación de bien", codigo_bien=codigo, detalle=motivo)

    flash(f"Bien '{codigo}' marcado como Observado.", "warning")
    return redirect(url_for("tic.bandeja"))


def _codigos_seleccionados() -> list[str]:
    return [c.strip() for c in request.form.getlist("codigos") if c.strip()]


@tic_bp.route("/tic/aprobar_lote", methods=["POST"])
@admin_o_editor_required
def aprobar_lote():
    usuario = usuario_actual()
    codigos = _codigos_seleccionados()
    nota = (request.form.get("nota") or "").strip()

    if not codigos:
        flash("No seleccionaste ningún bien para aprobar.", "danger")
        return redirect(url_for("tic.bandeja"))

    bienes = Inventario.query.filter(
        Inventario.codigo_bien.in_(codigos), Inventario.eliminado.is_(False)
    ).all()
    for bien in bienes:
        bien.estado = ESTADO_APROBADO
        bien.observaciones_tic = None
        bien.revisado_por_tic = usuario.username
        bien.fecha_revision_tic = datetime.utcnow()
    db.session.commit()

    registrar(usuario=usuario.username, accion="Aprobación masiva de bienes", detalle=(
        f"{len(bienes)} bien(es) aprobados en lote: " + ", ".join(b.codigo_bien for b in bienes)
        + (f" — Nota: {nota}" if nota else "")
    ))

    flash(f"{len(bienes)} bien(es) aprobados correctamente.", "success")
    return redirect(url_for("tic.bandeja"))


@tic_bp.route("/tic/observar_lote", methods=["POST"])
@admin_o_editor_required
def observar_lote():
    usuario = usuario_actual()
    codigos = _codigos_seleccionados()
    motivo = (request.form.get("motivo") or "").strip()

    if not codigos:
        flash("No seleccionaste ningún bien para observar.", "danger")
        return redirect(url_for("tic.bandeja"))
    if not motivo:
        flash("Debes indicar un motivo para observar los bienes seleccionados.", "danger")
        return redirect(url_for("tic.bandeja"))

    bienes = Inventario.query.filter(
        Inventario.codigo_bien.in_(codigos), Inventario.eliminado.is_(False)
    ).all()
    for bien in bienes:
        bien.estado = ESTADO_OBSERVADO
        bien.observaciones_tic = motivo
        bien.revisado_por_tic = usuario.username
        bien.fecha_revision_tic = datetime.utcnow()
    db.session.commit()

    registrar(usuario=usuario.username, accion="Observación masiva de bienes", detalle=(
        f"{len(bienes)} bien(es) observados en lote ({motivo}): " + ", ".join(b.codigo_bien for b in bienes)
    ))

    flash(f"{len(bienes)} bien(es) marcados como Observado.", "warning")
    return redirect(url_for("tic.bandeja"))
