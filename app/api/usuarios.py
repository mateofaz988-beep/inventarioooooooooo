from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models.usuario import ROLES_DISPONIBLES, Usuario
from app.utils.auditoria import registrar
from app.api.decorators import admin_o_editor_required_api, admin_required_api, usuario_desde_jwt

api_usuarios_bp = Blueprint("api_usuarios", __name__, url_prefix="/api/usuarios")


@api_usuarios_bp.route("", methods=["GET"])
@admin_o_editor_required_api
def listar():
    usuarios = Usuario.query.order_by(Usuario.username).all()
    return jsonify([u.to_dict() for u in usuarios]), 200


@api_usuarios_bp.route("", methods=["POST"])
@admin_o_editor_required_api
def crear():
    admin = usuario_desde_jwt()
    datos = request.get_json(silent=True) or {}
    username = (datos.get("username") or "").strip()
    password = datos.get("password") or ""
    rol = datos.get("rol") or ROLES_DISPONIBLES[1]

    if not username or not password:
        return jsonify({"error": "username y password son obligatorios"}), 400
    if Usuario.query.filter_by(username=username).first():
        return jsonify({"error": f"Ya existe un usuario con el nombre '{username}'"}), 409

    usuario = Usuario(
        username=username, rol=rol,
        nombre_completo=(datos.get("nombre_completo") or "").strip() or None,
        email=(datos.get("email") or "").strip() or None,
        activo=True,
    )
    usuario.set_password(password)
    db.session.add(usuario)
    db.session.commit()

    registrar(usuario=admin.username, accion="Creación de usuario (API)", detalle=f"Usuario '{username}' creado")

    return jsonify(usuario.to_dict()), 201


@api_usuarios_bp.route("/<int:usuario_id>", methods=["PUT", "PATCH"])
@admin_o_editor_required_api
def editar(usuario_id):
    admin = usuario_desde_jwt()
    usuario = Usuario.query.get(usuario_id)
    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404

    datos = request.get_json(silent=True) or {}
    if "username" in datos:
        nuevo_username = (datos.get("username") or "").strip()
        if not nuevo_username:
            return jsonify({"error": "El nombre de usuario no puede estar vacío"}), 400
        duplicado = Usuario.query.filter(Usuario.username == nuevo_username, Usuario.id != usuario.id).first()
        if duplicado:
            return jsonify({"error": f"Ya existe otro usuario con el nombre '{nuevo_username}'"}), 409
        usuario.username = nuevo_username
    if "rol" in datos:
        usuario.rol = datos.get("rol")
    if "nombre_completo" in datos:
        usuario.nombre_completo = (datos.get("nombre_completo") or "").strip() or None
    if "email" in datos:
        usuario.email = (datos.get("email") or "").strip() or None
    if "activo" in datos:
        usuario.activo = bool(datos.get("activo"))
    if datos.get("password"):
        usuario.set_password(datos["password"])

    db.session.commit()
    registrar(usuario=admin.username, accion="Edición de usuario (API)", detalle=f"Usuario '{usuario.username}' actualizado")

    return jsonify(usuario.to_dict()), 200


@api_usuarios_bp.route("/<int:usuario_id>", methods=["DELETE"])
@admin_required_api
def eliminar(usuario_id):
    admin = usuario_desde_jwt()
    if usuario_id == admin.id:
        return jsonify({"error": "No puedes eliminar tu propio usuario"}), 400

    usuario = Usuario.query.get(usuario_id)
    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404

    username = usuario.username
    db.session.delete(usuario)
    db.session.commit()

    registrar(usuario=admin.username, accion="Eliminación de usuario (API)", detalle=f"Usuario '{username}' eliminado")

    return jsonify({"mensaje": f"Usuario '{username}' eliminado"}), 200
