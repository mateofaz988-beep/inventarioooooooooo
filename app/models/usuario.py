from datetime import datetime

from app.extensions import bcrypt, db

ROL_ADMINISTRADOR = "Administrador"
ROL_EDITOR = "Editor"
ROL_TECNICO = "Tecnico Levantamiento"
ROLES_DISPONIBLES = [ROL_ADMINISTRADOR, ROL_EDITOR, ROL_TECNICO]


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(50), nullable=False, default=ROL_TECNICO)
    nombre_completo = db.Column(db.String(150), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    direccion = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def rol_normalizado(self) -> str:
        return (self.rol or "").strip().lower()

    @property
    def es_administrador(self) -> bool:
        return self.rol_normalizado == ROL_ADMINISTRADOR.lower()

    @property
    def es_editor(self) -> bool:
        return self.rol_normalizado == ROL_EDITOR.lower()

    @property
    def tiene_acceso_administrativo(self) -> bool:
        """Administrador o Editor: mismo nivel de acceso a las secciones
        administrativas (TIC, Inventario Previo, Auditoría, Usuarios).

        El Editor tiene todos los permisos del Administrador excepto eliminar
        registros; esa restricción se aplica aparte, no aquí (ver
        `puede_eliminar` en app.utils.permisos).
        """
        return self.es_administrador or self.es_editor

    @property
    def es_tecnico(self) -> bool:
        # Coincidencia por subcadena (acepta "tecnico" y "técnico"), igual que el sistema original.
        rol = self.rol_normalizado
        return "tecnico" in rol or "técnico" in rol

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "rol": self.rol,
            "nombre_completo": self.nombre_completo,
            "email": self.email,
            "direccion": self.direccion,
            "activo": self.activo,
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None,
        }

    def __repr__(self) -> str:
        return f"<Usuario {self.username} ({self.rol})>"
