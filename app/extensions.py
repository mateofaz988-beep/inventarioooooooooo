"""Instancias únicas de extensiones, compartidas entre la app web y la API.

Se definen aquí (sin importar app/__init__.py) para evitar imports circulares:
los modelos y blueprints importan `db`, `bcrypt`, `jwt` desde este módulo.
"""
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
cors = CORS()
csrf = CSRFProtect()
# Almacenamiento en memoria: suficiente para un despliegue de un solo proceso
# (esta app corre como servicio único en Windows, no distribuido). Si en el
# futuro se despliega con varios workers, cambiar a un backend compartido
# (ej. Redis) vía RATELIMIT_STORAGE_URI en la config.
limiter = Limiter(key_func=get_remote_address)
