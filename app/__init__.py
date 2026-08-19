from flask import Flask

from app.config import get_config
from app.extensions import bcrypt, cors, csrf, db, jwt, limiter


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    csrf.init_app(app)
    limiter.init_app(app)

    with app.app_context():
        from app import models  # noqa: F401  registra los modelos en SQLAlchemy

    from app.api import register_api_blueprints
    from app.web import register_web_blueprints

    register_web_blueprints(app)
    api_blueprints = register_api_blueprints(app)

    # La API JSON se autentica con JWT por header (Authorization: Bearer),
    # nunca con la cookie de sesión, así que no está expuesta a CSRF (que
    # explota que el navegador adjunte cookies automáticamente). Eximirla
    # evita que clientes API (curl, Postman, un futuro frontend Angular)
    # tengan que enviar un token CSRF que no tiene sentido para ellos.
    for blueprint in api_blueprints:
        csrf.exempt(blueprint)

    from app.utils.decorators import usuario_actual

    @app.context_processor
    def inyectar_usuario():
        return {"usuario_actual": usuario_actual()}

    from app.utils.zona_horaria import hora_ecuador

    app.jinja_env.filters["hora_ec"] = hora_ecuador

    return app
