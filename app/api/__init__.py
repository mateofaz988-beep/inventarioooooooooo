"""Registro de la capa de API JSON (JWT), pensada para un futuro frontend
desacoplado (ej. Angular) sin tocar la base de datos directamente.
"""
from flask import Flask, jsonify


def register_api_blueprints(app: Flask) -> list:
    from app.api.auth import api_auth_bp
    from app.api.bienes import api_bienes_bp
    from app.api.tic import api_tic_bp
    from app.api.usuarios import api_usuarios_bp

    blueprints = [api_auth_bp, api_bienes_bp, api_tic_bp, api_usuarios_bp]
    for blueprint in blueprints:
        app.register_blueprint(blueprint)

    @app.errorhandler(404)
    def _api_o_web_404(error):
        from flask import request
        if request.path.startswith("/api/"):
            return jsonify({"error": "Recurso no encontrado"}), 404
        return "Página no encontrada", 404

    return blueprints
