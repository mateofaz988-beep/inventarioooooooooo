from datetime import datetime

from app.extensions import db


class BitacoraAuditoria(db.Model):
    """Bitácora de auditoría. Guarda snapshots de texto, sin FK duras hacia
    `inventario` ni `usuarios`: el sistema audita después de eliminar un bien,
    y puede referenciar usuarios que ya no existen. Una FK estricta rompería esos flujos.
    """

    __tablename__ = "bitacora_auditoria"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    codigo_bien = db.Column(db.String(255), nullable=True, index=True)
    usuario = db.Column(db.String(80), nullable=True, index=True)
    accion = db.Column(db.String(100), nullable=False, index=True)
    detalle = db.Column(db.Text, nullable=True)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "codigo_bien": self.codigo_bien,
            "usuario": self.usuario,
            "accion": self.accion,
            "detalle": self.detalle,
            "fecha": self.fecha.isoformat() if self.fecha else None,
        }
