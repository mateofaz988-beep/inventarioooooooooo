from flask import Blueprint, render_template, request
from sqlalchemy import or_

from app.models.bitacora import BitacoraAuditoria
from app.utils.decorators import admin_o_editor_required

auditoria_bp = Blueprint("auditoria", __name__)


@auditoria_bp.route("/auditoria", methods=["GET"])
@admin_o_editor_required
def listar():
    termino = (request.args.get("q") or "").strip()

    consulta = BitacoraAuditoria.query
    if termino:
        patron = f"%{termino}%"
        consulta = consulta.filter(or_(
            BitacoraAuditoria.codigo_bien.ilike(patron),
            BitacoraAuditoria.usuario.ilike(patron),
            BitacoraAuditoria.accion.ilike(patron),
            BitacoraAuditoria.detalle.ilike(patron),
        ))

    eventos = consulta.order_by(BitacoraAuditoria.fecha.desc()).limit(200).all()
    return render_template("auditoria.html", eventos=eventos, termino=termino)
