from datetime import datetime

from app.extensions import db


class InventarioPrevio(db.Model):
    """Tabla de staging donde aterrizan las filas de un Excel importado.

    Nunca se escribe directo en `inventario` desde aquí: un administrador debe
    revisar/verificar y luego ejecutar la migración (upsert) hacia el
    inventario oficial. Tiene una columna por cada campo oficial de
    `inventario` (mismos nombres de atributo que el modelo Inventario, ver
    app/utils/campos.py) para no perder información rica del Excel entre la
    carga y la migración.
    """

    __tablename__ = "inventario_previo"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Código real si el Excel lo traía, o uno provisional generado por el
    # sistema (ver app/utils/excel_import.py) si venía vacío o con un valor
    # centinela tipo "SIN CODIGO ESBYE" / "INGRESAR".
    codigo_bien = db.Column(db.String(255), unique=True, nullable=False, index=True)
    codigo_generado = db.Column(db.Boolean, nullable=False, default=False)

    # --- Identificación ---
    codigo_anterior = db.Column(db.String(255), nullable=True)
    identificador = db.Column(db.String(255), nullable=True)
    nro_acta_matriz = db.Column(db.String(255), nullable=True)
    bld_o_bca = db.Column(db.String(255), nullable=True)
    bien = db.Column(db.String(255), nullable=True, index=True)
    serie_identificacion = db.Column(db.String(255), nullable=True)
    modelo_caracteristicas = db.Column(db.Text, nullable=True)
    marca_otros = db.Column(db.String(255), nullable=True)
    critico = db.Column(db.String(255), nullable=True)
    descripcion = db.Column(db.Text, nullable=True)

    # --- Valoración ---
    moneda = db.Column(db.String(255), nullable=True)
    valor_compra = db.Column(db.Numeric(14, 2), nullable=True)
    recompra = db.Column(db.String(255), nullable=True)
    valor_contable = db.Column(db.Numeric(14, 2), nullable=True)
    valor_residual = db.Column(db.Numeric(14, 2), nullable=True)
    valor_en_libros = db.Column(db.Numeric(14, 2), nullable=True)
    valor_depreciacion_acumulada = db.Column(db.Numeric(14, 2), nullable=True)
    cuenta_contable = db.Column(db.String(255), nullable=True)
    depreciable = db.Column(db.String(255), nullable=True)
    vida_util = db.Column(db.Integer, nullable=True)
    fecha_ultima_depreciacion = db.Column(db.Date, nullable=True)
    fecha_termino_depreciacion = db.Column(db.Date, nullable=True)

    # --- Características y condición ---
    color = db.Column(db.String(255), nullable=True)
    material = db.Column(db.String(255), nullable=True)
    dimensiones = db.Column(db.Text, nullable=True)
    condicion_bien = db.Column(db.String(255), nullable=True)
    habilitado = db.Column(db.String(255), nullable=True)
    estado_bien = db.Column(db.String(255), nullable=True, index=True)
    comodato = db.Column(db.String(255), nullable=True)
    item_renglon = db.Column(db.String(255), nullable=True)

    # --- Ubicación, custodia y actas ---
    id_bodega = db.Column(db.String(255), nullable=True)
    bodega = db.Column(db.String(255), nullable=True)
    id_ubicacion = db.Column(db.String(255), nullable=True)
    ubicacion_bodega = db.Column(db.String(255), nullable=True, index=True)
    nro_cedula_ruc = db.Column(db.String(255), nullable=True)
    custodio_actual = db.Column(db.String(255), nullable=True, index=True)
    custodio_activo = db.Column(db.String(255), nullable=True)
    origen_ingreso = db.Column(db.String(255), nullable=True)
    tipo_ingreso = db.Column(db.String(255), nullable=True)
    nro_compromiso = db.Column(db.String(255), nullable=True)
    estado_acta = db.Column(db.String(255), nullable=True)
    contabilizado_acta = db.Column(db.String(255), nullable=True)
    contabilizado_bien = db.Column(db.String(255), nullable=True)
    fecha_creacion = db.Column(db.Date, nullable=True)
    fecha_ingreso = db.Column(db.Date, nullable=True)

    # --- Control de la carga ---
    observaciones_carga = db.Column(db.Text, nullable=True)
    nombre_archivo_origen = db.Column(db.String(255), nullable=True)
    fecha_carga = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    verificado = db.Column(db.Boolean, nullable=False, default=False)
    usuario_verificador = db.Column(db.String(80), nullable=True)

    def to_dict(self) -> dict:
        from app.utils.campos import CAMPOS_BIEN

        data = {c["attr"]: _serializar(getattr(self, c["attr"])) for c in CAMPOS_BIEN}
        data.update({
            "id": self.id,
            "codigo_generado": self.codigo_generado,
            "observaciones_carga": self.observaciones_carga,
            "nombre_archivo_origen": self.nombre_archivo_origen,
            "fecha_carga": self.fecha_carga.isoformat() if self.fecha_carga else None,
            "verificado": self.verificado,
            "usuario_verificador": self.usuario_verificador,
        })
        return data


def _serializar(valor):
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    if hasattr(valor, "__float__") and not isinstance(valor, (int, float, str, bool, type(None))):
        return float(valor)
    return valor
