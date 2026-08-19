from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for

from app.extensions import db
from app.models.inventario import ESTADO_EN_REVISION, Inventario
from app.models.usuario import Usuario
from app.utils.auditoria import registrar
from app.utils.busqueda import aplicar_busqueda_texto
from app.utils.campos import CAMPOS_BIEN, TABS, TIPO_TEXTO
from app.utils.decorators import login_required, usuario_actual
from app.utils.excel_export import exportar_inventario_excel, nombre_archivo_exportacion
from app.utils.parsing import limpiar_texto_corto, parse_decimal, parse_entero, parse_fecha
from app.utils.permisos import campos_bloqueados_para, es_administrador

inventario_bp = Blueprint("inventario", __name__)

ITEMS_POR_PAGINA = 10


def _filtros_desde_request(args) -> dict:
    return {
        "q": (args.get("q") or "").strip(),
        "bodega": (args.get("bodega") or "").strip(),
        "estado_bien": (args.get("estado_bien") or "").strip(),
        "custodio": (args.get("custodio") or "").strip(),
        "fecha_desde": (args.get("fecha_desde") or "").strip(),
        "fecha_hasta": (args.get("fecha_hasta") or "").strip(),
    }


def _query_busqueda(filtros: dict):
    consulta = Inventario.query.filter(Inventario.eliminado.is_(False))

    if filtros.get("q"):
        consulta = aplicar_busqueda_texto(consulta, filtros["q"])
    if filtros.get("bodega"):
        consulta = consulta.filter(Inventario.bodega == filtros["bodega"])
    if filtros.get("estado_bien"):
        consulta = consulta.filter(Inventario.estado_bien == filtros["estado_bien"])
    if filtros.get("custodio"):
        consulta = consulta.filter(Inventario.custodio_actual.ilike(f"%{filtros['custodio']}%"))
    if filtros.get("fecha_desde"):
        fecha = parse_fecha(filtros["fecha_desde"])
        if fecha:
            consulta = consulta.filter(Inventario.fecha_ingreso >= fecha)
    if filtros.get("fecha_hasta"):
        fecha = parse_fecha(filtros["fecha_hasta"])
        if fecha:
            consulta = consulta.filter(Inventario.fecha_ingreso <= fecha)

    return consulta.order_by(Inventario.id.desc())


def _opciones_filtro(columna):
    filas = (
        db.session.query(columna)
        .filter(columna.isnot(None), columna != "", Inventario.eliminado.is_(False))
        .distinct()
        .order_by(columna)
        .all()
    )
    return [fila[0] for fila in filas]


@inventario_bp.route("/inventario", methods=["GET"])
@login_required
def listar():
    filtros = _filtros_desde_request(request.args)
    pagina = request.args.get("pagina", 1, type=int)

    consulta = _query_busqueda(filtros)
    total = consulta.count()
    total_paginas = max(1, (total + ITEMS_POR_PAGINA - 1) // ITEMS_POR_PAGINA)
    pagina = min(max(1, pagina), total_paginas)

    bienes = consulta.offset((pagina - 1) * ITEMS_POR_PAGINA).limit(ITEMS_POR_PAGINA).all()
    tecnicos = Usuario.query.filter_by(activo=True).order_by(Usuario.username).all()

    return render_template(
        "inventario.html",
        bienes=bienes,
        termino=filtros["q"],
        filtros=filtros,
        opciones_bodega=_opciones_filtro(Inventario.bodega),
        opciones_estado_bien=_opciones_filtro(Inventario.estado_bien),
        pagina=pagina,
        total_paginas=total_paginas,
        total=total,
        tabs=TABS,
        campos=CAMPOS_BIEN,
        tecnicos=tecnicos,
        campos_bloqueados=campos_bloqueados_para(usuario_actual()),
    )


@inventario_bp.route("/inventario/nuevo", methods=["POST"])
@login_required
def nuevo():
    usuario = usuario_actual()
    codigo_bien = (request.form.get("codigo_bien") or "").strip()

    if not codigo_bien:
        flash("El Código del Bien es obligatorio para crear un nuevo registro.", "danger")
        return redirect(url_for("inventario.listar"))

    if Inventario.query.filter_by(codigo_bien=codigo_bien).first():
        flash(f"Ya existe un bien con el código '{codigo_bien}'.", "danger")
        return redirect(url_for("inventario.listar"))

    bien = Inventario(codigo_bien=codigo_bien, estado=ESTADO_EN_REVISION, usuario_registro=usuario.username)
    _aplicar_campos_formulario(bien, request.form, incluir_codigo=False, campos_bloqueados=campos_bloqueados_para(usuario))

    db.session.add(bien)
    db.session.commit()

    registrar(usuario=usuario.username, accion="Creación de bien", codigo_bien=codigo_bien,
              detalle="Nuevo registro creado desde el formulario de inventario")

    flash(f"Bien '{codigo_bien}' creado correctamente con estado En Revisión.", "success")
    return redirect(url_for("inventario.listar"))


@inventario_bp.route("/inventario/eliminar/<codigo>", methods=["POST"])
@login_required
def eliminar(codigo):
    from datetime import datetime

    usuario = usuario_actual()
    if not es_administrador(usuario):
        flash("Acceso denegado: solo el Administrador puede eliminar bienes.", "danger")
        return redirect(url_for("inventario.listar"))

    bien = Inventario.query.filter_by(codigo_bien=codigo, eliminado=False).first_or_404()

    # Borrado lógico, no físico: un bien de control de activos con valor
    # contable no puede perder sus ~45 campos para siempre por error o mala
    # fe. El registro sigue existiendo (para auditoría/histórico) pero
    # desaparece de listados, búsquedas y exportaciones.
    bien.eliminado = True
    bien.fecha_eliminacion = datetime.utcnow()
    bien.eliminado_por = usuario.username
    db.session.commit()

    registrar(usuario=usuario.username, accion="Eliminación de bien", codigo_bien=codigo,
              detalle=f"Bien '{codigo}' marcado como eliminado (borrado lógico)")

    flash(f"Bien '{codigo}' eliminado correctamente.", "success")
    return redirect(url_for("inventario.listar"))


@inventario_bp.route("/inventario/exportar", methods=["GET"])
@login_required
def exportar():
    filtros = _filtros_desde_request(request.args)
    bienes = _query_busqueda(filtros).all()

    buffer = exportar_inventario_excel(bienes)
    nombre_archivo = nombre_archivo_exportacion(filtros["q"])

    registrar(usuario=usuario_actual().username, accion="Exportación de Excel", detalle=(
        f"Exportadas {len(bienes)} filas" + (f" (filtro: '{filtros['q']}')" if filtros["q"] else "")
    ))

    return send_file(
        buffer,
        as_attachment=True,
        download_name=nombre_archivo,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _aplicar_campos_formulario(
    bien: Inventario, form, incluir_codigo: bool = True, campos_bloqueados: frozenset = frozenset()
) -> None:
    from app.utils.campos import TIPO_DECIMAL, TIPO_ENTERO, TIPO_FECHA

    for campo in CAMPOS_BIEN:
        if campo["attr"] == "codigo_bien" and not incluir_codigo:
            continue
        if campo["attr"] in campos_bloqueados:
            continue
        if campo["attr"] not in form:
            continue
        valor_crudo = form.get(campo["attr"])
        if campo["tipo"] == TIPO_DECIMAL:
            valor = parse_decimal(valor_crudo)
        elif campo["tipo"] == TIPO_ENTERO:
            valor = parse_entero(valor_crudo)
        elif campo["tipo"] == TIPO_FECHA:
            valor = parse_fecha(valor_crudo)
        elif campo["tipo"] == TIPO_TEXTO:
            valor = limpiar_texto_corto(valor_crudo)
        else:
            valor = (valor_crudo or "").strip() or None
        setattr(bien, campo["attr"], valor)
