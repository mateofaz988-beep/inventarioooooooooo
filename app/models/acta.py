from datetime import datetime

from app.extensions import db


class Acta(db.Model):
    """Registro inmutable de cada acta consolidada emitida.

    `id` funciona directamente como el número de acta correlativo: usar el
    AUTO_INCREMENT nativo de InnoDB evita la condición de carrera de calcular
    "MAX(nro_acta) + 1" a mano bajo escrituras concurrentes.

    `bienes_snapshot` guarda los datos de los bienes TAL COMO ESTABAN al
    emitirse el acta (no una referencia a `inventario`, a propósito, igual
    que `bitacora_auditoria`): si un bien cambia de estado, valor o incluso
    se elimina después, reimprimir esta acta debe seguir mostrando exactamente
    lo que se firmó, no el estado actual del inventario.
    """

    __tablename__ = "actas"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    custodio = db.Column(db.String(255), nullable=False, index=True)
    usuario_elabora = db.Column(db.String(80), nullable=False)
    elaborado_nombre = db.Column(db.String(150), nullable=True)
    elaborado_direccion = db.Column(db.String(255), nullable=True)
    fecha_emision = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    total_bienes = db.Column(db.Integer, nullable=False)
    total_valor = db.Column(db.Numeric(14, 2), nullable=False)
    bienes_snapshot = db.Column(db.JSON, nullable=False)

    @property
    def nro_acta(self) -> int:
        return self.id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nro_acta": self.nro_acta,
            "custodio": self.custodio,
            "usuario_elabora": self.usuario_elabora,
            "elaborado_nombre": self.elaborado_nombre,
            "elaborado_direccion": self.elaborado_direccion,
            "fecha_emision": self.fecha_emision.isoformat() if self.fecha_emision else None,
            "total_bienes": self.total_bienes,
            "total_valor": float(self.total_valor) if self.total_valor is not None else None,
        }
