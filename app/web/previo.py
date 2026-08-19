import os

from flask import Blueprint, flash, redirect, render_template, request, send_file, session, url_for
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.inventario_previo import InventarioPrevio
from app.utils.auditoria import registrar
from app.utils.decorators import admin_o_editor_required, usuario_actual
from app.utils.excel_export import generar_plantilla_excel
from app.utils.excel_import import EXTENSIONES_PERMITIDAS, ExcelInvalidoError, cargar_a_staging, migrar_a_inventario

previo_bp = Blueprint("previo", __name__)

ITEMS_POR_PAGINA = 25


@previo_bp.route("/inventario-previo", methods=["GET"])
@admin_o_editor_required
def listar():
    termino = (request.args.get("q") or "").strip()
    estado_filtro = (request.args.get("verificado") or "").strip()
    pagina = request.args.get("pagina", 1, type=int)

    consulta = InventarioPrevio.query
    if termino:
        patron = f"%{termino}%"
        consulta = consulta.filter(or_(
            InventarioPrevio.codigo_bien.ilike(patron),
            InventarioPrevio.codigo_anterior.ilike(patron),
            InventarioPrevio.identificador.ilike(patron),
            InventarioPrevio.bien.ilike(patron),
            InventarioPrevio.serie_identificacion.ilike(patron),
            InventarioPrevio.marca_otros.ilike(patron),
            InventarioPrevio.estado_bien.ilike(patron),
            InventarioPrevio.bodega.ilike(patron),
            InventarioPrevio.ubicacion_bodega.ilike(patron),
            InventarioPrevio.custodio_actual.ilike(patron),
            InventarioPrevio.custodio_activo.ilike(patron),
            InventarioPrevio.nro_cedula_ruc.ilike(patron),
            InventarioPrevio.nombre_archivo_origen.ilike(patron),
        ))
    if estado_filtro == "pendientes":
        consulta = consulta.filter_by(verificado=False)
    elif estado_filtro == "verificados":
        consulta = consulta.filter_by(verificado=True)

    total = consulta.count()
    total_paginas = max(1, (total + ITEMS_POR_PAGINA - 1) // ITEMS_POR_PAGINA)
    pagina = min(max(1, pagina), total_paginas)

    filas = (
        consulta.order_by(InventarioPrevio.fecha_carga.desc(), InventarioPrevio.id.desc())
        .offset((pagina - 1) * ITEMS_POR_PAGINA)
        .limit(ITEMS_POR_PAGINA)
        .all()
    )

    kpi_total = InventarioPrevio.query.count()
    kpi_pendientes = InventarioPrevio.query.filter_by(verificado=False).count()
    kpi_verificados = kpi_total - kpi_pendientes
    kpi_sin_codigo = InventarioPrevio.query.filter_by(codigo_generado=True).count()

    resumen_carga = session.pop("resumen_carga", None)
    resumen_migracion = session.pop("resumen_migracion", None)
    return render_template(
        "previo.html", filas=filas, resumen_carga=resumen_carga, resumen_migracion=resumen_migracion,
        termino=termino, estado_filtro=estado_filtro, pagina=pagina, total_paginas=total_paginas, total=total,
        kpi_total=kpi_total, kpi_pendientes=kpi_pendientes, kpi_verificados=kpi_verificados,
        kpi_sin_codigo=kpi_sin_codigo,
    )


@previo_bp.route("/inventario-previo/plantilla", methods=["GET"])
@admin_o_editor_required
def plantilla():
    buffer = generar_plantilla_excel()
    registrar(usuario=usuario_actual().username, accion="Descarga de plantilla Excel", detalle=None)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="plantilla_inventario_inamhi.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@previo_bp.route("/inventario-previo/cargar", methods=["GET", "POST"])
@admin_o_editor_required
def cargar():
    if request.method == "POST":
        archivo = request.files.get("archivo_excel")
        usuario = usuario_actual()

        if archivo is None or archivo.filename == "":
            flash("Debes seleccionar un archivo Excel (.xlsx o .xls).", "danger")
            return redirect(url_for("previo.cargar"))

        extension = os.path.splitext(secure_filename(archivo.filename))[1].lower()
        if extension not in EXTENSIONES_PERMITIDAS:
            flash("Formato no admitido. Solo se aceptan archivos .xlsx o .xls.", "danger")
            return redirect(url_for("previo.cargar"))

        nombre_archivo = secure_filename(archivo.filename)
        try:
            resumen = cargar_a_staging(archivo, usuario.username, nombre_archivo=nombre_archivo)
        except ExcelInvalidoError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("previo.cargar"))

        session["resumen_carga"] = resumen.to_dict()
        flash(
            f"Carga completada: {resumen.filas_leidas} filas leídas, {resumen.nuevas} nuevas, "
            f"{resumen.actualizadas} actualizadas, {resumen.sin_codigo_provisional} sin código "
            f"(se les asignó uno provisional), {resumen.omitidas} omitidas (filas vacías).",
            "success",
        )
        return redirect(url_for("previo.listar"))

    return render_template("cargar_previo.html")


@previo_bp.route("/inventario-previo/validar/<int:fila_id>", methods=["POST"])
@admin_o_editor_required
def validar(fila_id):
    usuario = usuario_actual()
    fila = InventarioPrevio.query.get_or_404(fila_id)

    fila.verificado = True
    fila.usuario_verificador = usuario.username
    db.session.commit()

    registrar(usuario=usuario.username, accion="Verificación de fila previa", codigo_bien=fila.codigo_bien,
              detalle="Fila marcada como verificada en inventario previo")

    flash(f"Fila '{fila.codigo_bien}' marcada como verificada.", "success")
    return redirect(url_for("previo.listar"))


@previo_bp.route("/inventario-previo/validar-todo", methods=["POST"])
@admin_o_editor_required
def validar_todo():
    usuario = usuario_actual()
    pendientes = InventarioPrevio.query.filter_by(verificado=False)
    total = pendientes.count()

    pendientes.update({
        InventarioPrevio.verificado: True,
        InventarioPrevio.usuario_verificador: usuario.username,
    }, synchronize_session=False)
    db.session.commit()

    registrar(usuario=usuario.username, accion="Verificación masiva de inventario previo",
              detalle=f"{total} fila(s) marcadas como verificadas de una sola vez")

    flash(f"{total} fila(s) marcadas como verificadas.", "success")
    return redirect(url_for("previo.listar"))


@previo_bp.route("/inventario-previo/migrar", methods=["POST"])
@admin_o_editor_required
def migrar():
    usuario = usuario_actual()
    resumen = migrar_a_inventario(usuario.username)

    session["resumen_migracion"] = resumen.to_dict()
    flash(
        f"Migración completada: {resumen.insertados} insertados, {resumen.actualizados} actualizados, "
        f"{resumen.omitidos} omitidos (no verificados).",
        "success",
    )
    return redirect(url_for("previo.listar"))
