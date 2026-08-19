"""Registro de todos los blueprints de páginas HTML (Jinja2 + sesión de Flask)."""
from flask import Flask, redirect, session, url_for


def register_web_blueprints(app: Flask) -> None:
    from app.web.acta import acta_bp
    from app.web.auditoria import auditoria_bp
    from app.web.auth import auth_bp
    from app.web.editar import editar_bp
    from app.web.inventario import inventario_bp
    from app.web.previo import previo_bp
    from app.web.tic import tic_bp
    from app.web.usuarios import usuarios_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(inventario_bp)
    app.register_blueprint(editar_bp)
    app.register_blueprint(tic_bp)
    app.register_blueprint(auditoria_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(acta_bp)
    app.register_blueprint(previo_bp)

    @app.route("/")
    def raiz():
        if session.get("usuario_id"):
            return redirect(url_for("inventario.listar"))
        return redirect(url_for("auth.login"))
