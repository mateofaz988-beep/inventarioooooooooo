"""Definición centralizada de los campos del bien de inventario.

Esta es la ÚNICA fuente de verdad sobre:
  - el nombre de atributo Python (attr) <-> el nombre de columna oficial en español (label),
  - en qué pestaña del formulario aparece cada campo,
  - qué tipo de dato tiene (para parseo seguro desde Excel/formularios),
  - qué alias de encabezado de Excel se aceptan al importar,
  - qué campos son obligatorios para un envío "En Revisión" (definitivo).

Los blueprints web/API, la exportación/importación de Excel y los templates
recorren esta lista en vez de tener los nombres de columna repetidos y
hardcodeados en varios lugares.
"""
from collections import OrderedDict

TIPO_TEXTO = "texto"
TIPO_TEXTAREA = "textarea"
TIPO_DECIMAL = "decimal"
TIPO_FECHA = "fecha"
TIPO_ENTERO = "entero"

# Cada entrada: attr, label (nombre exacto de columna en MySQL), tab, tipo, aliases (para import Excel)
CAMPOS_BIEN = [
    # --- Pestaña 1: Identificación ---
    {"attr": "codigo_bien", "label": "Código del Bien", "tab": "identificacion", "tipo": TIPO_TEXTO,
     "requerido": True,
     "aliases": ["Código del Bien", "Código del Bien Esbye", "codigo_bien", "CODIGO", "Codigo del Bien", "Código"]},
    {"attr": "codigo_anterior", "label": "Código Anterior", "tab": "identificacion", "tipo": TIPO_TEXTO,
     "aliases": ["Código Anterior", "codigo_anterior", "CODIGO ANTERIOR"]},
    {"attr": "identificador", "label": "Identificador", "tab": "identificacion", "tipo": TIPO_TEXTO,
     "aliases": ["Identificador"]},
    {"attr": "nro_acta_matriz", "label": "Nro de Acta/ Nro de Matriz", "tab": "identificacion", "tipo": TIPO_TEXTO,
     "aliases": ["Nro de Acta/ Nro de Matriz", "Nro de Acta", "Nro de Matriz", "Nro. Acta"]},
    {"attr": "bld_o_bca", "label": "(BLD) o (BCA)", "tab": "identificacion", "tipo": TIPO_TEXTO,
     "requerido": True,
     "aliases": ["(BLD) o (BCA)", "BLD o BCA", "BLD/BCA"]},
    {"attr": "bien", "label": "Bien", "tab": "identificacion", "tipo": TIPO_TEXTO,
     "requerido": True,
     "aliases": ["Bien", "Nombre del Bien", "Descripción", "DETALLE", "ESTACION"]},
    {"attr": "serie_identificacion", "label": "Serie/ Identificación", "tab": "identificacion", "tipo": TIPO_TEXTO,
     "requerido": True,
     "aliases": ["Serie/ Identificación", "Serie", "Identificación", "SERIE"]},
    {"attr": "modelo_caracteristicas", "label": "Modelo/ Características", "tab": "identificacion", "tipo": TIPO_TEXTAREA,
     "aliases": ["Modelo/ Características", "Modelo", "Características"]},
    {"attr": "marca_otros", "label": "Marca/ Otros", "tab": "identificacion", "tipo": TIPO_TEXTO,
     "aliases": ["Marca/ Otros", "Marca"]},
    {"attr": "critico", "label": "Crítico", "tab": "identificacion", "tipo": TIPO_TEXTO,
     "aliases": ["Crítico"]},
    {"attr": "descripcion", "label": "Descripción", "tab": "identificacion", "tipo": TIPO_TEXTAREA,
     "aliases": ["Descripción", "DETALLE"]},

    # --- Pestaña 2: Valoración ---
    {"attr": "moneda", "label": "Moneda", "tab": "valoracion", "tipo": TIPO_TEXTO,
     "aliases": ["Moneda"]},
    {"attr": "valor_compra", "label": "Valor de Compra", "tab": "valoracion", "tipo": TIPO_DECIMAL,
     "aliases": ["Valor de Compra", "VALOR"]},
    {"attr": "recompra", "label": "Recompra", "tab": "valoracion", "tipo": TIPO_TEXTO,
     "aliases": ["Recompra"]},
    {"attr": "valor_contable", "label": "Valor Contable", "tab": "valoracion", "tipo": TIPO_DECIMAL,
     "aliases": ["Valor Contable"]},
    {"attr": "valor_residual", "label": "Valor Residual", "tab": "valoracion", "tipo": TIPO_DECIMAL,
     "aliases": ["Valor Residual"]},
    {"attr": "valor_en_libros", "label": "Valor en Libros", "tab": "valoracion", "tipo": TIPO_DECIMAL,
     "aliases": ["Valor en Libros"]},
    {"attr": "valor_depreciacion_acumulada", "label": "Valor Depreciación Acumulada", "tab": "valoracion",
     "tipo": TIPO_DECIMAL, "aliases": ["Valor Depreciación Acumulada"]},
    {"attr": "cuenta_contable", "label": "Cuenta Contable", "tab": "valoracion", "tipo": TIPO_TEXTO,
     "aliases": ["Cuenta Contable"]},
    {"attr": "depreciable", "label": "Depreciable", "tab": "valoracion", "tipo": TIPO_TEXTO,
     "aliases": ["Depreciable"]},
    {"attr": "vida_util", "label": "Vida Útil", "tab": "valoracion", "tipo": TIPO_ENTERO,
     "aliases": ["Vida Útil"]},
    {"attr": "fecha_ultima_depreciacion", "label": "Fecha Última Depreciación", "tab": "valoracion",
     "tipo": TIPO_FECHA, "aliases": ["Fecha Última Depreciación"]},
    {"attr": "fecha_termino_depreciacion", "label": "Fecha Término Depreciación", "tab": "valoracion",
     "tipo": TIPO_FECHA, "aliases": ["Fecha Término Depreciación"]},

    # --- Pestaña 3: Características físicas y condición ---
    {"attr": "color", "label": "Color", "tab": "caracteristicas", "tipo": TIPO_TEXTO,
     "aliases": ["Color"]},
    {"attr": "material", "label": "Material", "tab": "caracteristicas", "tipo": TIPO_TEXTO,
     "aliases": ["Material"]},
    {"attr": "dimensiones", "label": "Dimensiones", "tab": "caracteristicas", "tipo": TIPO_TEXTAREA,
     "aliases": ["Dimensiones"]},
    {"attr": "condicion_bien", "label": "Condición del Bien", "tab": "caracteristicas", "tipo": TIPO_TEXTO,
     "aliases": ["Condición del Bien", "Estado", "Condicion del Bien"]},
    {"attr": "habilitado", "label": "Habilitado", "tab": "caracteristicas", "tipo": TIPO_TEXTO,
     "aliases": ["Habilitado"]},
    {"attr": "estado_bien", "label": "Estado Bien", "tab": "caracteristicas", "tipo": TIPO_TEXTO,
     "requerido": True,
     "aliases": ["Estado Bien"]},
    {"attr": "comodato", "label": "Comodato", "tab": "caracteristicas", "tipo": TIPO_TEXTO,
     "aliases": ["Comodato"]},
    {"attr": "item_renglon", "label": "Item/ Renglón", "tab": "caracteristicas", "tipo": TIPO_TEXTO,
     "aliases": ["Item/ Renglón", "Item"]},

    # --- Pestaña 4: Ubicación, custodia y actas ---
    {"attr": "id_bodega", "label": "Id Bodega", "tab": "ubicacion", "tipo": TIPO_TEXTO,
     "aliases": ["Id Bodega"]},
    {"attr": "bodega", "label": "Bodega", "tab": "ubicacion", "tipo": TIPO_TEXTO,
     "aliases": ["Bodega"]},
    {"attr": "id_ubicacion", "label": "Id Ubicación", "tab": "ubicacion", "tipo": TIPO_TEXTO,
     "aliases": ["Id Ubicación"]},
    {"attr": "ubicacion_bodega", "label": "Ubicación de Bodega", "tab": "ubicacion", "tipo": TIPO_TEXTO,
     "requerido": True,
     "aliases": [
         # Encabezados "M_..." (prefijo usado por MATRIZ_COMPLETA_INAMHI.xlsx para las
         # columnas de referencia/histórico) deben ir DESPUÉS de sus equivalentes sin
         # prefijo: se usa el primer alias con dato no vacío por fila, y la columna
         # oficial siempre debe tener prioridad sobre la de respaldo.
         "Ubicación de Bodega", "UBICACIÓN 2026", "UBICACIÓN 2025", "ubicacion_previa",
         "Ubicación 2024", "UBICACIÓN INFORME", "UBICACIÓN GENERAL2",
         "M_UBICACIÓN 2025", "M_Ubicación 2024", "M_UBICACIÓN INFORME", "M_UBICACIÓN GENERAL2",
     ]},
    {"attr": "nro_cedula_ruc", "label": "Nro de Cédula/ RUC", "tab": "ubicacion", "tipo": TIPO_TEXTO,
     "aliases": ["Nro de Cédula/ RUC", "Cédula", "RUC", "CEDULA", "Cedula"]},
    {"attr": "custodio_actual", "label": "Custodio Actual", "tab": "ubicacion", "tipo": TIPO_TEXTO,
     "requerido": True,
     "aliases": [
         "Custodio Actual", "USUARIO 2025", "USUARIO 2024", "custodio_previo", "ESBYE 2025 ACTUAL",
         "M_USUARIO 2025", "M_USUARIO 2024", "M_ESBYE 2025 ACTUAL",
     ]},
    {"attr": "custodio_activo", "label": "Custodio Activo", "tab": "ubicacion", "tipo": TIPO_TEXTO,
     "aliases": ["Custodio Activo"]},
    {"attr": "origen_ingreso", "label": "Origen del Ingreso", "tab": "ubicacion", "tipo": TIPO_TEXTO,
     "aliases": ["Origen del Ingreso"]},
    {"attr": "tipo_ingreso", "label": "Tipo de Ingreso", "tab": "ubicacion", "tipo": TIPO_TEXTO,
     "aliases": ["Tipo de Ingreso"]},
    {"attr": "nro_compromiso", "label": "Nro de Compromiso", "tab": "ubicacion", "tipo": TIPO_TEXTO,
     "aliases": ["Nro de Compromiso"]},
    {"attr": "estado_acta", "label": "Estado del Acta", "tab": "ubicacion", "tipo": TIPO_TEXTO,
     "aliases": ["Estado del Acta"]},
    {"attr": "contabilizado_acta", "label": "Contabilizado del Acta", "tab": "ubicacion", "tipo": TIPO_TEXTO,
     "aliases": ["Contabilizado del Acta"]},
    {"attr": "contabilizado_bien", "label": "Contabilizado del Bien", "tab": "ubicacion", "tipo": TIPO_TEXTO,
     "aliases": ["Contabilizado del Bien"]},
    {"attr": "fecha_creacion", "label": "Fecha de Creación", "tab": "ubicacion", "tipo": TIPO_FECHA,
     "aliases": ["Fecha de Creación"]},
    {"attr": "fecha_ingreso", "label": "Fecha de Ingreso", "tab": "ubicacion", "tipo": TIPO_FECHA,
     "aliases": ["Fecha de Ingreso"]},
]

CAMPOS_POR_ATTR = OrderedDict((c["attr"], c) for c in CAMPOS_BIEN)

CAMPOS_REQUERIDOS = [c["attr"] for c in CAMPOS_BIEN if c.get("requerido")]

LABEL_A_ATTR = {c["label"]: c["attr"] for c in CAMPOS_BIEN}

# Orden EXACTO y oficial de las columnas de la tabla `inventario` (idéntico al
# especificado por la institución). Se usa para el DDL en MySQL y para que el
# Excel exportado tenga siempre las columnas en el mismo orden que la tabla
# real, de modo que se pueda reabrir/reimportar sin fricción.
ORDEN_COLUMNAS_OFICIAL = [
    "Código del Bien", "Código Anterior", "Identificador", "Nro de Acta/ Nro de Matriz",
    "(BLD) o (BCA)", "Bien", "Serie/ Identificación", "Modelo/ Características", "Marca/ Otros",
    "Crítico", "Moneda", "Valor de Compra", "Recompra", "Color", "Material", "Dimensiones",
    "Condición del Bien", "Habilitado", "Estado Bien", "Id Bodega", "Bodega", "Id Ubicación",
    "Ubicación de Bodega", "Nro de Cédula/ RUC", "Custodio Actual", "Custodio Activo",
    "Origen del Ingreso", "Tipo de Ingreso", "Nro de Compromiso", "Estado del Acta",
    "Contabilizado del Acta", "Contabilizado del Bien", "Descripción", "Item/ Renglón",
    "Cuenta Contable", "Depreciable", "Fecha de Creación", "Fecha de Ingreso",
    "Fecha Última Depreciación", "Vida Útil", "Fecha Término Depreciación", "Valor Contable",
    "Valor Residual", "Valor en Libros", "Valor Depreciación Acumulada", "Comodato",
]

CAMPOS_EN_ORDEN_OFICIAL = [CAMPOS_POR_ATTR[LABEL_A_ATTR[label]] for label in ORDEN_COLUMNAS_OFICIAL]

TABS = OrderedDict([
    ("identificacion", "Identificación"),
    ("valoracion", "Valoración"),
    ("caracteristicas", "Características y Condición"),
    ("ubicacion", "Ubicación y Custodia"),
])


def campos_por_tab(tab: str):
    return [c for c in CAMPOS_BIEN if c["tab"] == tab]
