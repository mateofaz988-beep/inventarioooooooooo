from app.extensions import db
from app.models.bitacora import BitacoraAuditoria


def registrar(usuario: str, accion: str, codigo_bien: str | None = None, detalle: str | None = None,
              commit: bool = True) -> BitacoraAuditoria:
    """Agrega una entrada a la bitácora de auditoría.

    No lleva FK hacia inventario/usuarios (son snapshots de texto), por lo que
    puede llamarse después de eliminar un bien o para usuarios ya eliminados.
    """
    entrada = BitacoraAuditoria(
        codigo_bien=codigo_bien,
        usuario=usuario,
        accion=accion,
        detalle=detalle,
    )
    db.session.add(entrada)
    if commit:
        db.session.commit()
    return entrada
