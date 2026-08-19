"""Decoradores de autenticación/autorización para las páginas HTML (sesión de Flask).

La capa /api/ usa JWT y sus propios decoradores (flask_jwt_extended), definidos
en app/api/auth.py — comparten el mismo modelo Usuario pero no esta sesión de cookies.
"""
from functools import wraps

from flask import flash, redirect, session, url_for

from app.models.usuario import Usuario
from app.utils.permisos import es_administrador, es_administrador_o_editor


def usuario_actual() -> Usuario | None:
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return None
    return Usuario.query.get(usuario_id)


def login_required(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        usuario = usuario_actual()
        if usuario is None or not usuario.activo:
            flash("Debes iniciar sesión para continuar.", "warning")
            return redirect(url_for("auth.login"))
        return vista(*args, **kwargs)

    return envoltura


def admin_required(vista):
    """Acceso restringido al Administrador (rol estricto), sin excepciones.

    Reservar para acciones irreversibles (eliminar bienes/usuarios). Para el
    resto de secciones administrativas (TIC, Previo, Auditoría, gestión de
    usuarios salvo el borrado), usar `admin_o_editor_required`.
    """
    @wraps(vista)
    def envoltura(*args, **kwargs):
        usuario = usuario_actual()
        if usuario is None or not usuario.activo:
            flash("Debes iniciar sesión para continuar.", "warning")
            return redirect(url_for("auth.login"))
        if not es_administrador(usuario):
            flash("Acceso denegado: se requiere rol Administrador.", "danger")
            return redirect(url_for("inventario.listar"))
        return vista(*args, **kwargs)

    return envoltura


def admin_o_editor_required(vista):
    """Administrador o Editor: el Editor tiene el mismo nivel de acceso
    administrativo que el Administrador, excepto eliminar registros (las
    rutas de borrado usan `admin_required`, no este decorador)."""
    @wraps(vista)
    def envoltura(*args, **kwargs):
        usuario = usuario_actual()
        if usuario is None or not usuario.activo:
            flash("Debes iniciar sesión para continuar.", "warning")
            return redirect(url_for("auth.login"))
        if not es_administrador_o_editor(usuario):
            flash("Acceso denegado: se requiere rol Administrador o Editor.", "danger")
            return redirect(url_for("inventario.listar"))
        return vista(*args, **kwargs)

    return envoltura
