from datetime import datetime

from app.extensions import db


class BienHistorialCustodio(db.Model):
    """Traza cada cambio de custodio de un bien: quién lo tenía, a quién pasó,
    quién hizo el cambio y cuándo.

    Sin FK hacia `inventario` a propósito (mismo criterio que
    `bitacora_auditoria`): un bien puede eliminarse (borrado lógico) o
    cambiar de código, y el historial de traspasos debe sobrevivir a eso.
    """

    __tablename__ = "bien_historial_custodio"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    codigo_bien = db.Column(db.String(255), nullable=False, index=True)
    custodio_anterior = db.Column(db.String(255), nullable=True)
    custodio_nuevo = db.Column(db.String(255), nullable=True)
    usuario_modifica = db.Column(db.String(80), nullable=True)
    fecha_traspaso = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "codigo_bien": self.codigo_bien,
            "custodio_anterior": self.custodio_anterior,
            "custodio_nuevo": self.custodio_nuevo,
            "usuario_modifica": self.usuario_modifica,
            "fecha_traspaso": self.fecha_traspaso.isoformat() if self.fecha_traspaso else None,
        }
