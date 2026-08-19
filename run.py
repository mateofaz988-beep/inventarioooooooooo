"""Punto de entrada de la aplicación.

El esquema de la base de datos se crea con sql/schema.sql en MySQL Workbench
(ver README). Este archivo solo levanta el servidor Flask de desarrollo.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=app.config.get("DEBUG", False),
        use_reloader=False,
        threaded=True,
    )
