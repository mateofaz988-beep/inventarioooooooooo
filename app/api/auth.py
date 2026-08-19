from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required

from app.models.usuario import Usuario
from app.utils.auditoria import registrar
from app.api.decorators import usuario_desde_jwt

api_auth_bp = Blueprint("api_auth", __name__, url_prefix="/api/auth")


@api_auth_bp.route("/login", methods=["POST"])
def login():
    datos = request.get_json(silent=True) or {}
    username = (datos.get("username") or "").strip()
    password = datos.get("password") or ""

    if not username or not password:
        return jsonify({"error": "username y password son obligatorios"}), 400

    usuario = Usuario.query.filter_by(username=username).first()
    if usuario is None or not usuario.activo or not usuario.check_password(password):
        return jsonify({"error": "Credenciales inválidas"}), 401

    token = create_access_token(identity=str(usuario.id))
    registrar(usuario=usuario.username, accion="Inicio de sesión (API)", detalle=None)

    return jsonify({"access_token": token, "usuario": usuario.to_dict()}), 200


@api_auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    usuario = usuario_desde_jwt()
    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify(usuario.to_dict()), 200
