from datetime import datetime

from app.extensions import db

ESTADO_BORRADOR = "Borrador"
ESTADO_EN_REVISION = "En Revisión"
ESTADO_OBSERVADO = "Observado"
ESTADO_APROBADO = "Aprobado"
ESTADOS_VALIDOS = [ESTADO_BORRADOR, ESTADO_EN_REVISION, ESTADO_OBSERVADO, ESTADO_APROBADO]


class Inventario(db.Model):
    __tablename__ = "inventario"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # --- Identificación ---
    codigo_bien = db.Column("Código del Bien", db.String(255), unique=True, nullable=False, index=True)
    codigo_anterior = db.Column("Código Anterior", db.String(255), nullable=True)
    identificador = db.Column("Identificador", db.String(255), nullable=True)
    nro_acta_matriz = db.Column("Nro de Acta/ Nro de Matriz", db.String(255), nullable=True)
    bld_o_bca = db.Column("(BLD) o (BCA)", db.String(255), nullable=True)
    bien = db.Column("Bien", db.String(255), nullable=True, index=True)
    serie_identificacion = db.Column("Serie/ Identificación", db.String(255), nullable=True)
    modelo_caracteristicas = db.Column("Modelo/ Características", db.Text, nullable=True)
    marca_otros = db.Column("Marca/ Otros", db.String(255), nullable=True)
    critico = db.Column("Crítico", db.String(255), nullable=True)
    descripcion = db.Column("Descripción", db.Text, nullable=True)

    # --- Valoración ---
    moneda = db.Column("Moneda", db.String(255), nullable=True)
    valor_compra = db.Column("Valor de Compra", db.Numeric(14, 2), nullable=True)
    recompra = db.Column("Recompra", db.String(255), nullable=True)
    valor_contable = db.Column("Valor Contable", db.Numeric(14, 2), nullable=True)
    valor_residual = db.Column("Valor Residual", db.Numeric(14, 2), nullable=True)
    valor_en_libros = db.Column("Valor en Libros", db.Numeric(14, 2), nullable=True)
    valor_depreciacion_acumulada = db.Column("Valor Depreciación Acumulada", db.Numeric(14, 2), nullable=True)
    cuenta_contable = db.Column("Cuenta Contable", db.String(255), nullable=True)
    depreciable = db.Column("Depreciable", db.String(255), nullable=True)
    vida_util = db.Column("Vida Útil", db.Integer, nullable=True)
    fecha_ultima_depreciacion = db.Column("Fecha Última Depreciación", db.Date, nullable=True)
    fecha_termino_depreciacion = db.Column("Fecha Término Depreciación", db.Date, nullable=True)

    # --- Características y condición ---
    color = db.Column("Color", db.String(255), nullable=True)
    material = db.Column("Material", db.String(255), nullable=True)
    dimensiones = db.Column("Dimensiones", db.Text, nullable=True)
    condicion_bien = db.Column("Condición del Bien", db.String(255), nullable=True)
    habilitado = db.Column("Habilitado", db.String(255), nullable=True)
    estado_bien = db.Column("Estado Bien", db.String(255), nullable=True, index=True)
    comodato = db.Column("Comodato", db.String(255), nullable=True)
    item_renglon = db.Column("Item/ Renglón", db.String(255), nullable=True)

    # --- Ubicación, custodia y actas ---
    id_bodega = db.Column("Id Bodega", db.String(255), nullable=True)
    bodega = db.Column("Bodega", db.String(255), nullable=True)
    id_ubicacion = db.Column("Id Ubicación", db.String(255), nullable=True)
    ubicacion_bodega = db.Column("Ubicación de Bodega", db.String(255), nullable=True)
    nro_cedula_ruc = db.Column("Nro de Cédula/ RUC", db.String(255), nullable=True)
    custodio_actual = db.Column("Custodio Actual", db.String(255), nullable=True, index=True)
    custodio_activo = db.Column("Custodio Activo", db.String(255), nullable=True)
    origen_ingreso = db.Column("Origen del Ingreso", db.String(255), nullable=True)
    tipo_ingreso = db.Column("Tipo de Ingreso", db.String(255), nullable=True)
    nro_compromiso = db.Column("Nro de Compromiso", db.String(255), nullable=True)
    estado_acta = db.Column("Estado del Acta", db.String(255), nullable=True)
    contabilizado_acta = db.Column("Contabilizado del Acta", db.String(255), nullable=True)
    contabilizado_bien = db.Column("Contabilizado del Bien", db.String(255), nullable=True)
    fecha_creacion = db.Column("Fecha de Creación", db.Date, nullable=True)
    fecha_ingreso = db.Column("Fecha de Ingreso", db.Date, nullable=True)

    # --- Flujo de trabajo (control interno, no viene del Excel) ---
    usuario_registro = db.Column("Usuario Registro", db.String(80), nullable=True, index=True)
    estado = db.Column("estado", db.String(50), nullable=False, default=ESTADO_EN_REVISION, index=True)
    observaciones_tic = db.Column("observaciones_tic", db.Text, nullable=True)
    fecha_revision_tic = db.Column("fecha_revision_tic", db.DateTime, nullable=True)
    revisado_por_tic = db.Column("revisado_por_tic", db.String(80), nullable=True)

    # --- Borrado lógico ---
    # "Eliminar" nunca hace DELETE físico: un bien de control de activos con
    # valor contable no puede perder sus ~45 campos para siempre por error o
    # mala fe. Todas las consultas de listado deben filtrar eliminado=False;
    # el registro sigue existiendo para auditoría/histórico.
    eliminado = db.Column("eliminado", db.Boolean, nullable=False, default=False, index=True)
    fecha_eliminacion = db.Column("fecha_eliminacion", db.DateTime, nullable=True)
    eliminado_por = db.Column("eliminado_por", db.String(80), nullable=True)

    def to_dict(self) -> dict:
        from app.utils.campos import CAMPOS_BIEN

        data = {c["attr"]: _serializar(getattr(self, c["attr"])) for c in CAMPOS_BIEN}
        data.update({
            "id": self.id,
            "usuario_registro": self.usuario_registro,
            "estado": self.estado,
            "observaciones_tic": self.observaciones_tic,
            "fecha_revision_tic": self.fecha_revision_tic.isoformat() if self.fecha_revision_tic else None,
            "revisado_por_tic": self.revisado_por_tic,
        })
        return data

    def __repr__(self) -> str:
        return f"<Inventario {self.codigo_bien}>"


def _serializar(valor):
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    if hasattr(valor, "__float__") and not isinstance(valor, (int, float, str, bool, type(None))):
        return float(valor)
    return valor
