from datetime import datetime

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models.inventario import ESTADO_APROBADO, ESTADO_OBSERVADO, Inventario
from app.utils.auditoria import registrar
from app.api.decorators import admin_o_editor_required_api, usuario_desde_jwt

api_tic_bp = Blueprint("api_tic", __name__, url_prefix="/api/tic")


@api_tic_bp.route("/aprobar", methods=["POST"])
@admin_o_editor_required_api
def aprobar():
    usuario = usuario_desde_jwt()
    datos = request.get_json(silent=True) or {}
    codigo = (datos.get("codigo_bien") or "").strip()
    nota = (datos.get("nota") or "").strip()

    bien = Inventario.query.filter_by(codigo_bien=codigo).first()
    if bien is None:
        return jsonify({"error": "Bien no encontrado"}), 404

    bien.estado = ESTADO_APROBADO
    bien.observaciones_tic = None
    bien.revisado_por_tic = usuario.username
    bien.fecha_revision_tic = datetime.utcnow()
    db.session.commit()

    registrar(usuario=usuario.username, accion="Aprobación de bien (API)", codigo_bien=codigo, detalle=nota or None)

    return jsonify(bien.to_dict()), 200


@api_tic_bp.route("/observar", methods=["POST"])
@admin_o_editor_required_api
def observar():
    usuario = usuario_desde_jwt()
    datos = request.get_json(silent=True) or {}
    codigo = (datos.get("codigo_bien") or "").strip()
    motivo = (datos.get("motivo") or "").strip()

    if not motivo:
        return jsonify({"error": "El motivo de observación es obligatorio"}), 400

    bien = Inventario.query.filter_by(codigo_bien=codigo).first()
    if bien is None:
        return jsonify({"error": "Bien no encontrado"}), 404

    bien.estado = ESTADO_OBSERVADO
    bien.observaciones_tic = motivo
    bien.revisado_por_tic = usuario.username
    bien.fecha_revision_tic = datetime.utcnow()
    db.session.commit()

    registrar(usuario=usuario.username, accion="Observación de bien (API)", codigo_bien=codigo, detalle=motivo)

    return jsonify(bien.to_dict()), 200
