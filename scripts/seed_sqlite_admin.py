"""Prepara un entorno LOCAL de SQLite para levantar el sistema en una máquina
que no tiene MySQL instalado/configurado (por ejemplo, para revisar o probar
el sistema en una PC distinta a la que sí tiene MySQL Workbench conectado).

Qué hace:
  1. Crea las 6 tablas del sistema en un archivo .sqlite3 local (mismo
     esquema que sql/schema.sql, generado desde los modelos SQLAlchemy).
  2. Crea un usuario Administrador de prueba si todavía no existe:
         usuario:    admin123
         contraseña: contraseña123456

Es idempotente: se puede volver a ejecutar sin duplicar tablas ni usuarios
(si "admin123" ya existe, no lo toca ni resetea su contraseña).

Requisito: tu archivo .env local debe tener `DB_ENGINE=sqlite` (ver
.env.example). El script se niega a correr si detecta que el .env apunta a
MySQL, precisamente para no arriesgarse a tocar una base de datos real por
error -- en una máquina con MySQL configurado (ej. la otra PC), este script
simplemente no debe usarse.

Uso:
    python scripts\\seed_sqlite_admin.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.config import get_config
from app.extensions import db
from app.models.usuario import ROL_ADMINISTRADOR, Usuario

ADMIN_USERNAME = "admin123"
ADMIN_PASSWORD = "contraseña123456"


def main() -> None:
    cfg = get_config()
    if getattr(cfg, "DB_ENGINE", "mysql") != "sqlite":
        print(
            "Este .env NO tiene DB_ENGINE=sqlite (está usando MySQL). Este "
            "script es solo para el modo local sin MySQL: agrega DB_ENGINE=sqlite "
            "a tu .env si de verdad quieres crear una base de datos local, o "
            "ignora este script si esta máquina ya se conecta a tu MySQL real."
        )
        sys.exit(1)

    app = create_app()
    with app.app_context():
        db.create_all()
        print(f"Base de datos SQLite lista en: {app.config['SQLALCHEMY_DATABASE_URI']}")

        existente = Usuario.query.filter_by(username=ADMIN_USERNAME).first()
        if existente:
            print(f"El usuario '{ADMIN_USERNAME}' ya existe (rol: {existente.rol}); no se modifica.")
            return

        admin = Usuario(
            username=ADMIN_USERNAME,
            rol=ROL_ADMINISTRADOR,
            nombre_completo="Administrador (local de prueba)",
            activo=True,
        )
        admin.set_password(ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()

        print(f"Usuario Administrador de prueba creado: '{ADMIN_USERNAME}' / '{ADMIN_PASSWORD}'")
        print("Ya puedes iniciar el servidor con: python run.py")


if __name__ == "__main__":
    main()
