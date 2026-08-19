from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for

from app.extensions import db
from app.models.usuario import ROLES_DISPONIBLES, Usuario
from app.utils.auditoria import registrar
from app.utils.backup import RespaldoError, generar_respaldo
from app.utils.decorators import admin_o_editor_required, admin_required, usuario_actual
from app.utils.permisos import puede_asignar_rol, puede_gestionar_cuenta

usuarios_bp = Blueprint("usuarios", __name__)


@usuarios_bp.route("/usuarios", methods=["GET"])
@admin_o_editor_required
def listar():
    usuarios = Usuario.query.order_by(Usuario.username).all()
    return render_template("usuarios.html", usuarios=usuarios, roles=ROLES_DISPONIBLES)


@usuarios_bp.route("/usuarios/crear", methods=["POST"])
@admin_o_editor_required
def crear():
    admin = usuario_actual()
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    rol = request.form.get("rol") or ROLES_DISPONIBLES[1]
    nombre_completo = (request.form.get("nombre_completo") or "").strip() or None
    email = (request.form.get("email") or "").strip() or None
    direccion = (request.form.get("direccion") or "").strip() or None

    if not username or not password:
        flash("Usuario y contraseña son obligatorios.", "danger")
        return redirect(url_for("usuarios.listar"))

    if not puede_asignar_rol(admin, rol):
        flash("Acceso denegado: solo el Administrador puede crear otra cuenta con rol Administrador.", "danger")
        return redirect(url_for("usuarios.listar"))

    if Usuario.query.filter_by(username=username).first():
        flash(f"Ya existe un usuario con el nombre '{username}'.", "danger")
        return redirect(url_for("usuarios.listar"))

    nuevo_usuario = Usuario(
        username=username, rol=rol, nombre_completo=nombre_completo, email=email,
        direccion=direccion, activo=True,
    )
    nuevo_usuario.set_password(password)
    db.session.add(nuevo_usuario)
    db.session.commit()

    registrar(usuario=admin.username, accion="Creación de usuario", detalle=f"Usuario '{username}' creado con rol '{rol}'")

    flash(f"Usuario '{username}' creado correctamente.", "success")
    return redirect(url_for("usuarios.listar"))


@usuarios_bp.route("/usuarios/editar/<int:usuario_id>", methods=["POST"])
@admin_o_editor_required
def editar(usuario_id):
    admin = usuario_actual()
    usuario = Usuario.query.get_or_404(usuario_id)

    if not puede_gestionar_cuenta(admin, usuario):
        flash("Acceso denegado: solo el Administrador puede modificar una cuenta Administrador.", "danger")
        return redirect(url_for("usuarios.listar"))

    username = (request.form.get("username") or "").strip()
    rol = request.form.get("rol") or usuario.rol
    nombre_completo = (request.form.get("nombre_completo") or "").strip() or None
    email = (request.form.get("email") or "").strip() or None
    direccion = (request.form.get("direccion") or "").strip() or None

    if not username:
        flash("El nombre de usuario no puede estar vacío.", "danger")
        return redirect(url_for("usuarios.listar"))

    if not puede_asignar_rol(admin, rol):
        flash("Acceso denegado: solo el Administrador puede otorgar el rol Administrador.", "danger")
        return redirect(url_for("usuarios.listar"))

    duplicado = Usuario.query.filter(Usuario.username == username, Usuario.id != usuario.id).first()
    if duplicado:
        flash(f"Ya existe otro usuario con el nombre '{username}'.", "danger")
        return redirect(url_for("usuarios.listar"))

    usuario.username = username
    usuario.rol = rol
    usuario.nombre_completo = nombre_completo
    usuario.email = email
    usuario.direccion = direccion
    db.session.commit()

    registrar(usuario=admin.username, accion="Edición de usuario", detalle=f"Usuario '{username}' actualizado (rol: '{rol}')")

    flash(f"Usuario '{username}' actualizado correctamente.", "success")
    return redirect(url_for("usuarios.listar"))


@usuarios_bp.route("/usuarios/cambiar_password/<int:usuario_id>", methods=["POST"])
@admin_o_editor_required
def cambiar_password(usuario_id):
    admin = usuario_actual()
    usuario = Usuario.query.get_or_404(usuario_id)

    if not puede_gestionar_cuenta(admin, usuario):
        flash("Acceso denegado: solo el Administrador puede cambiar la contraseña de una cuenta Administrador.", "danger")
        return redirect(url_for("usuarios.listar"))

    nueva_password = request.form.get("password") or ""

    if not nueva_password or len(nueva_password) < 6:
        flash("La nueva contraseña debe tener al menos 6 caracteres.", "danger")
        return redirect(url_for("usuarios.listar"))

    usuario.set_password(nueva_password)
    db.session.commit()

    registrar(admin.username, "Cambio de contraseña", detalle=f"Contraseña actualizada para '{usuario.username}'")

    flash(f"Contraseña de '{usuario.username}' actualizada correctamente.", "success")
    return redirect(url_for("usuarios.listar"))


@usuarios_bp.route("/usuarios/eliminar/<int:usuario_id>", methods=["POST"])
@admin_required
def eliminar(usuario_id):
    admin = usuario_actual()
    usuario = Usuario.query.get_or_404(usuario_id)

    if usuario.id == admin.id:
        flash("No puedes eliminar tu propio usuario.", "danger")
        return redirect(url_for("usuarios.listar"))

    username = usuario.username
    db.session.delete(usuario)
    db.session.commit()

    registrar(admin.username, "Eliminación de usuario", detalle=f"Usuario '{username}' eliminado")

    flash(f"Usuario '{username}' eliminado correctamente.", "success")
    return redirect(url_for("usuarios.listar"))


@usuarios_bp.route("/usuarios/respaldo", methods=["POST"])
@admin_required
def respaldo():
    """Genera un respaldo de la base de datos (mysqldump) bajo demanda y lo
    ofrece para descarga inmediata. `app/utils/backup.py` ya implementaba
    esto, pero solo podía invocarse a mano desde una shell de Python (ver
    README) — sin un disparador en la interfaz, en la práctica nunca se
    ejecutaba. También queda registrado en la bitácora de auditoría.
    """
    admin = usuario_actual()
    try:
        ruta = generar_respaldo(current_app.config)
    except RespaldoError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("usuarios.listar"))

    registrar(usuario=admin.username, accion="Respaldo de base de datos",
              detalle=f"Archivo generado: {ruta.name}")

    return send_file(ruta, as_attachment=True, download_name=ruta.name, mimetype="application/sql")
