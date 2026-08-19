"""Reglas de autorización, compartidas entre las páginas HTML (sesión) y la API (JWT).

Los checks de rol se hacen siempre normalizados (lowercase + strip), y el rol
técnico matchea por subcadena ("tecnico" o "técnico"), tal como en el sistema original.
"""
from app.models.inventario import ESTADO_APROBADO
from app.models.usuario import ROL_ADMINISTRADOR, ROL_EDITOR, Usuario


def normalizar_rol(rol: str | None) -> str:
    return (rol or "").strip().lower()


def es_administrador(usuario: Usuario | None) -> bool:
    return bool(usuario) and normalizar_rol(usuario.rol) == ROL_ADMINISTRADOR.lower()


def es_editor(usuario: Usuario | None) -> bool:
    return bool(usuario) and normalizar_rol(usuario.rol) == ROL_EDITOR.lower()


def es_administrador_o_editor(usuario: Usuario | None) -> bool:
    """El Editor tiene el mismo nivel de acceso administrativo que el
    Administrador (crear, editar, visualizar, exportar, aprobar/observar en
    TIC, gestionar usuarios, etc.), con la única excepción de eliminar
    registros: ver `puede_eliminar`.
    """
    return es_administrador(usuario) or es_editor(usuario)


def puede_eliminar(usuario: Usuario | None) -> bool:
    """Solo el Administrador (rol estricto) puede eliminar registros.

    Esta es la única capacidad que el rol Editor NO hereda del Administrador.
    Se usa tanto para ocultar/deshabilitar los botones de eliminar en la UI
    como para bloquear la invocación de las rutas de borrado en el backend.
    """
    return es_administrador(usuario)


# Campos del bien que solo el Administrador puede crear/modificar. El Editor
# (y cualquier otro rol) los ve de solo lectura: son datos de control de acta/
# custodia con implicancia legal, fuera del alcance de "control absoluto"
# que el Editor sí tiene sobre el resto del formulario.
CAMPOS_RESTRINGIDOS_EDITOR = frozenset({
    "custodio_activo", "origen_ingreso", "tipo_ingreso", "nro_compromiso", "estado_acta",
})


def campos_bloqueados_para(usuario: Usuario | None) -> frozenset[str]:
    """Nombres de atributo (`CAMPOS_BIEN[].attr`) que este usuario NO puede
    crear ni editar. Se usa tanto para renderizar esos campos como
    solo-lectura en los formularios como para ignorarlos si igual llegan en
    el POST/JSON (el HTML `readonly` no es una barrera real de seguridad).
    """
    if es_administrador(usuario):
        return frozenset()
    return CAMPOS_RESTRINGIDOS_EDITOR


def puede_asignar_rol(actor: Usuario | None, rol_destino: str | None) -> bool:
    """Solo el Administrador (rol estricto) puede otorgar el rol Administrador
    a un usuario, sea al crearlo o al editarlo.

    Sin este check, `admin_o_editor_required` deja crear/editar usuarios a
    cualquier Editor, que entonces podría auto-otorgarse (o darle a un
    tercero) el rol más alto del sistema con un simple POST — una escalada de
    privilegios completa a partir de una cuenta no administrativa.
    """
    if normalizar_rol(rol_destino) == ROL_ADMINISTRADOR.lower():
        return es_administrador(actor)
    return True


def puede_gestionar_cuenta(actor: Usuario | None, usuario_objetivo: Usuario | None) -> bool:
    """El Editor no puede modificar (rol, contraseña, datos) ni una cuenta que
    YA es Administrador, aunque `admin_o_editor_required` le permita llegar a
    esas rutas. Sin esto, un Editor podría degradar el rol del Administrador
    real o resetearle la contraseña (toma de control de la cuenta), ya que
    esas rutas no exigen rol estricto de Administrador.
    """
    if usuario_objetivo is not None and es_administrador(usuario_objetivo):
        return es_administrador(actor)
    return True


def es_tecnico(usuario: Usuario | None) -> bool:
    if not usuario:
        return False
    rol = normalizar_rol(usuario.rol)
    return "tecnico" in rol or "técnico" in rol


def puede_editar_bien(usuario: Usuario, bien) -> bool:
    """Un bien Aprobado queda bloqueado salvo para Administrador o Editor.

    Puede editar: el Administrador, el Editor, quien registró el bien, el
    custodio actual asignado, o cualquier usuario con rol Técnico Levantamiento.
    """
    if es_administrador_o_editor(usuario):
        return True

    if bien.estado == ESTADO_APROBADO:
        return False

    if bien.usuario_registro and bien.usuario_registro == usuario.username:
        return True

    if bien.custodio_actual and bien.custodio_actual == usuario.username:
        return True

    if es_tecnico(usuario):
        return True

    return False
