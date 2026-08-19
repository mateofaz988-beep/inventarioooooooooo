from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.extensions import db
from app.models.bien_historial_custodio import BienHistorialCustodio
from app.models.inventario import ESTADO_APROBADO, ESTADO_BORRADOR, ESTADO_EN_REVISION, Inventario
from app.models.usuario import Usuario
from app.utils.auditoria import registrar
from app.utils.campos import CAMPOS_BIEN, CAMPOS_POR_ATTR, CAMPOS_REQUERIDOS, TABS
from app.utils.decorators import login_required, usuario_actual
from app.utils.permisos import campos_bloqueados_para, es_administrador, puede_editar_bien
from app.web.inventario import _aplicar_campos_formulario

editar_bp = Blueprint("editar", __name__)


@editar_bp.route("/editar/<codigo>", methods=["GET", "POST"])
@login_required
def editar(codigo):
    bien = Inventario.query.filter_by(codigo_bien=codigo, eliminado=False).first_or_404()
    usuario = usuario_actual()

    if not puede_editar_bien(usuario, bien):
        if bien.estado == ESTADO_APROBADO:
            flash("Acceso denegado: este bien ya está Aprobado y solo el Administrador puede editarlo.", "danger")
        else:
            flash("Acceso denegado: no tienes permisos para editar este bien.", "danger")
        return redirect(url_for("inventario.listar"))

    campos_bloqueados = campos_bloqueados_para(usuario)
    historial_custodio = (
        BienHistorialCustodio.query.filter_by(codigo_bien=codigo)
        .order_by(BienHistorialCustodio.fecha_traspaso.desc())
        .all()
    )

    if request.method == "POST":
        estado_revision = (request.form.get("estado_revision") or "").strip()
        if estado_revision not in (ESTADO_BORRADOR, ESTADO_EN_REVISION):
            estado_revision = ESTADO_BORRADOR

        if estado_revision == ESTADO_EN_REVISION:
            faltantes = [
                CAMPOS_POR_ATTR[attr]["label"]
                for attr in CAMPOS_REQUERIDOS
                if not (request.form.get(attr) or "").strip()
            ]
            if faltantes:
                mensaje = "Faltan campos obligatorios: " + ", ".join(faltantes)
                flash(mensaje, "danger")
                tecnicos = Usuario.query.filter_by(activo=True).order_by(Usuario.username).all()
                return render_template(
                    "editar_bien.html", bien=bien, tabs=TABS, campos=CAMPOS_BIEN,
                    tecnicos=tecnicos, es_admin=es_administrador(usuario), campos_bloqueados=campos_bloqueados,
                    historial_custodio=historial_custodio,
                ), 400

        custodio_anterior = bien.custodio_actual
        _aplicar_campos_formulario(bien, request.form, incluir_codigo=False, campos_bloqueados=campos_bloqueados)
        bien.estado = estado_revision

        if bien.custodio_actual != custodio_anterior:
            db.session.add(BienHistorialCustodio(
                codigo_bien=bien.codigo_bien, custodio_anterior=custodio_anterior,
                custodio_nuevo=bien.custodio_actual, usuario_modifica=usuario.username,
            ))

        db.session.commit()

        registrar(usuario=usuario.username, accion="Edición de bien", codigo_bien=bien.codigo_bien,
                  detalle=f"Guardado como '{estado_revision}'")

        flash(f"Bien '{bien.codigo_bien}' guardado como '{estado_revision}'.", "success")
        return redirect(url_for("inventario.listar"))

    tecnicos = Usuario.query.filter_by(activo=True).order_by(Usuario.username).all()
    return render_template(
        "editar_bien.html", bien=bien, tabs=TABS, campos=CAMPOS_BIEN,
        tecnicos=tecnicos, es_admin=es_administrador(usuario), campos_bloqueados=campos_bloqueados,
        historial_custodio=historial_custodio,
    )
