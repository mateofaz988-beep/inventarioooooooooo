"""Importación de Excel hacia la tabla de staging (`inventario_previo`) y
migración (upsert con fusión) desde el staging hacia el inventario oficial
(`inventario`).

Flujo en dos pasos, nunca directo a producción:
    Excel -> leer_excel() -> cargar_a_staging() -> [revisión humana] -> migrar_a_inventario()

Diseñado para adaptarse a CUALQUIER matriz que suba el usuario, no solo al
formato oficial: cada campo de `CAMPOS_BIEN` puede tener varios encabezados
candidatos (sus "aliases", ver app/utils/campos.py); si el Excel trae más de
un candidato para el mismo campo (p.ej. "Ubicación 2025" y "Ubicación 2024"),
se usa el primero no vacío por fila, no una sola columna fija para todo el
archivo.
"""
import secrets
from dataclasses import dataclass, field

import pandas as pd

from app.extensions import db
from app.models.inventario import ESTADO_APROBADO, ESTADO_EN_REVISION, Inventario
from app.models.inventario_previo import InventarioPrevio
from app.utils.auditoria import registrar
from app.utils.campos import CAMPOS_BIEN, TIPO_DECIMAL, TIPO_ENTERO, TIPO_FECHA, TIPO_TEXTO
from app.utils.parsing import (
    contar_campos_llenos, limpiar_codigo, limpiar_texto, limpiar_texto_corto,
    parse_decimal, parse_entero, parse_fecha,
)

EXTENSIONES_PERMITIDAS = {".xlsx", ".xls"}

PARSERS = {
    TIPO_DECIMAL: parse_decimal,
    TIPO_ENTERO: parse_entero,
    TIPO_FECHA: parse_fecha,
    # TIPO_TEXTO son columnas VARCHAR(255): se recortan en vez de fallar toda
    # la carga si el Excel trae una descripción larga en un campo corto.
    TIPO_TEXTO: limpiar_texto_corto,
}

PREFIJO_CODIGO_PROVISIONAL = "SIN-CODIGO-"


class ExcelInvalidoError(Exception):
    pass


@dataclass
class ResumenCarga:
    filas_leidas: int = 0
    nuevas: int = 0
    actualizadas: int = 0
    sin_codigo_provisional: int = 0
    omitidas: int = 0
    detalles_omitidas: list = field(default_factory=list)

    def to_dict(self):
        return {
            "filas_leidas": self.filas_leidas,
            "nuevas": self.nuevas,
            "actualizadas": self.actualizadas,
            "sin_codigo_provisional": self.sin_codigo_provisional,
            "omitidas": self.omitidas,
            "detalles_omitidas": self.detalles_omitidas[:50],  # evita respuestas gigantes
        }


@dataclass
class ResumenMigracion:
    insertados: int = 0
    actualizados: int = 0
    omitidos: int = 0
    detalles_omitidos: list = field(default_factory=list)

    def to_dict(self):
        return {
            "insertados": self.insertados,
            "actualizados": self.actualizados,
            "omitidos": self.omitidos,
            "detalles_omitidos": self.detalles_omitidos[:50],
        }


def leer_excel(file_storage) -> pd.DataFrame:
    """Lee un archivo .xlsx/.xls con pandas. Soporta archivos grandes (~20k filas)."""
    try:
        df = pd.read_excel(file_storage, engine=None)
    except Exception as exc:  # noqa: BLE001 - queremos un mensaje claro al usuario
        raise ExcelInvalidoError(f"No se pudo leer el archivo Excel: {exc}") from exc

    df.columns = [str(c).strip() for c in df.columns]
    return df


def _mapa_columnas_por_campo(columnas_excel) -> dict:
    """Para cada campo de CAMPOS_BIEN, resuelve la lista (en orden de
    prioridad) de columnas reales del Excel que podrían tener su valor.
    Varias columnas candidatas por campo permiten que, fila por fila, se use
    la primera que tenga dato (p.ej. "Ubicación 2025" y si está vacía
    "Ubicación 2024"), en vez de fijar una sola columna para todo el archivo.
    """
    normalizadas = {}
    for c in columnas_excel:
        normalizadas.setdefault(str(c).strip().lower(), c)

    mapa = {}
    for campo in CAMPOS_BIEN:
        candidatas = []
        for alias in campo["aliases"]:
            columna_real = normalizadas.get(alias.strip().lower())
            if columna_real is not None and columna_real not in candidatas:
                candidatas.append(columna_real)
        if candidatas:
            mapa[campo["attr"]] = candidatas
    return mapa


def _extraer_fila(row: pd.Series, mapa: dict) -> dict:
    """Para cada campo, toma el primer valor no vacío entre sus columnas
    candidatas en esta fila, y lo parsea según el tipo del campo."""
    datos = {}
    for campo in CAMPOS_BIEN:
        columnas_candidatas = mapa.get(campo["attr"], [])
        valor_crudo = None
        for columna in columnas_candidatas:
            crudo = row.get(columna)
            if limpiar_texto(crudo) is not None:
                valor_crudo = crudo
                break

        parser = PARSERS.get(campo["tipo"], limpiar_texto)
        datos[campo["attr"]] = parser(valor_crudo)

    return datos


def _generar_codigo_provisional(codigos_usados: set) -> str:
    while True:
        candidato = f"{PREFIJO_CODIGO_PROVISIONAL}{secrets.token_hex(4).upper()}"
        if candidato not in codigos_usados:
            codigos_usados.add(candidato)
            return candidato


def _deduplicar_por_codigo(filas: list, codigos_usados: set) -> dict:
    """Si un código se repite en varias filas del Excel (mismo activo
    registrado en años/áreas distintas), nos quedamos con la fila MÁS
    COMPLETA (más campos llenos); en empate, con la que aparece más abajo en
    el archivo (más reciente). Nunca con la primera fila encontrada — de lo
    contrario se pisan datos buenos con filas viejas y vacías.

    Las filas sin código válido (vacío o un valor centinela tipo
    "SIN CODIGO ESBYE"/"INGRESAR") reciben un código provisional único cada
    una, en vez de agruparse entre sí: son bienes distintos, no duplicados.
    """
    mejores: dict[str, dict] = {}

    for indice, fila in enumerate(filas):
        codigo = fila["codigo_bien"]
        codigo_generado = False
        if not codigo:
            codigo = _generar_codigo_provisional(codigos_usados)
            codigo_generado = True
        else:
            codigos_usados.add(codigo)

        puntaje = (contar_campos_llenos(fila), indice)

        if codigo_generado:
            # Cada fila sin código real es un bien potencialmente distinto:
            # no se agrupa con otras filas sin código.
            fila_final = dict(fila)
            fila_final["codigo_bien"] = codigo
            fila_final["_codigo_generado"] = True
            fila_final["_puntaje"] = puntaje
            mejores[codigo] = fila_final
            continue

        actual = mejores.get(codigo)
        if actual is None or puntaje >= actual["_puntaje"]:
            fila_final = dict(fila)
            fila_final["codigo_bien"] = codigo
            fila_final["_codigo_generado"] = False
            fila_final["_puntaje"] = puntaje
            mejores[codigo] = fila_final

    for fila in mejores.values():
        fila.pop("_puntaje", None)

    return mejores


def cargar_a_staging(file_storage, usuario: str, nombre_archivo: str | None = None) -> ResumenCarga:
    df = leer_excel(file_storage)
    resumen = ResumenCarga(filas_leidas=len(df))

    mapa = _mapa_columnas_por_campo(df.columns)
    if "codigo_bien" not in mapa:
        aliases_codigo = next(c["aliases"] for c in CAMPOS_BIEN if c["attr"] == "codigo_bien")
        raise ExcelInvalidoError(
            "El Excel no tiene ninguna columna reconocible como 'Código del Bien'. "
            "Encabezados admitidos: " + ", ".join(aliases_codigo)
        )

    filas_extraidas = []
    for numero_fila, row in df.iterrows():
        fila = _extraer_fila(row, mapa)
        fila["codigo_bien"] = limpiar_codigo(fila["codigo_bien"])

        if contar_campos_llenos(fila) == 0:
            # Fila completamente vacía (frecuente al final de un Excel real):
            # no es un bien, se descarta en vez de crear un registro basura
            # con código provisional.
            resumen.omitidas += 1
            resumen.detalles_omitidas.append(f"Fila {numero_fila + 2}: completamente vacía")
            continue

        filas_extraidas.append(fila)

    codigos_existentes_db = {
        c for (c,) in db.session.query(InventarioPrevio.codigo_bien).all()
    } | {c for (c,) in db.session.query(Inventario.codigo_bien).all()}

    deduplicadas = _deduplicar_por_codigo(filas_extraidas, set(codigos_existentes_db))

    codigos = list(deduplicadas.keys())
    existentes = {
        registro.codigo_bien: registro
        for lote_inicio in range(0, len(codigos), 500)
        for registro in InventarioPrevio.query.filter(
            InventarioPrevio.codigo_bien.in_(codigos[lote_inicio:lote_inicio + 500])
        ).all()
    } if codigos else {}

    for codigo, fila in deduplicadas.items():
        codigo_generado = fila.pop("_codigo_generado", False)
        registro = existentes.get(codigo)
        if registro is None:
            registro = InventarioPrevio(codigo_bien=codigo)
            db.session.add(registro)
            resumen.nuevas += 1
        else:
            resumen.actualizadas += 1

        if codigo_generado:
            resumen.sin_codigo_provisional += 1

        for campo in CAMPOS_BIEN:
            if campo["attr"] == "codigo_bien":
                continue
            setattr(registro, campo["attr"], fila.get(campo["attr"]))

        registro.codigo_generado = codigo_generado
        registro.nombre_archivo_origen = nombre_archivo
        nota = f"Cargado desde Excel por {usuario}"
        if codigo_generado:
            nota += " — código provisional asignado por el sistema (el Excel no traía un código válido)"
        registro.observaciones_carga = nota
        registro.verificado = False
        registro.usuario_verificador = None

    db.session.commit()

    registrar(
        usuario=usuario,
        accion="Importación de Excel",
        detalle=(
            f"Archivo: {nombre_archivo or '(sin nombre)'} — filas leídas: {resumen.filas_leidas}, "
            f"nuevas: {resumen.nuevas}, actualizadas: {resumen.actualizadas}, "
            f"sin código (provisional asignado): {resumen.sin_codigo_provisional}"
        ),
    )

    return resumen


def migrar_a_inventario(usuario: str) -> ResumenMigracion:
    """Hace upsert por código desde `inventario_previo` (solo filas
    verificadas) hacia `inventario`. Es idempotente: reintentar no duplica
    nada porque `codigo_bien` es único y se busca antes de insertar.

    Fusión automática: si el bien ya existe en el inventario oficial, solo se
    sobrescriben los campos para los que el staging trae un valor no vacío —
    los campos que el staging trae vacíos NO borran datos que ya existían en
    el inventario oficial. Así, subir una matriz nueva sobre datos ya
    cargados los complementa/actualiza en vez de vaciarlos.
    """
    resumen = ResumenMigracion()

    filas = InventarioPrevio.query.filter_by(verificado=True).all()
    total_no_verificadas = InventarioPrevio.query.filter_by(verificado=False).count()
    if total_no_verificadas:
        resumen.omitidos += total_no_verificadas
        resumen.detalles_omitidos.append(f"{total_no_verificadas} fila(s) no verificadas, se omiten")

    if not filas:
        return resumen

    codigos = [f.codigo_bien for f in filas]
    existentes = {
        bien.codigo_bien: bien
        for lote_inicio in range(0, len(codigos), 500)
        for bien in Inventario.query.filter(
            Inventario.codigo_bien.in_(codigos[lote_inicio:lote_inicio + 500])
        ).all()
    }

    for fila in filas:
        bien = existentes.get(fila.codigo_bien)
        es_nuevo = bien is None
        if es_nuevo:
            bien = Inventario(codigo_bien=fila.codigo_bien, estado=ESTADO_EN_REVISION, usuario_registro=usuario)
            db.session.add(bien)
            existentes[fila.codigo_bien] = bien
            resumen.insertados += 1
        else:
            if bien.eliminado:
                # El código coincide con un bien borrado lógicamente: re-subir
                # el mismo código a través del flujo oficial de staging es una
                # re-alta deliberada, así que se reactiva en vez de quedar
                # como un registro "zombie" invisible para siempre.
                bien.eliminado = False
                bien.fecha_eliminacion = None
                bien.eliminado_por = None
            resumen.actualizados += 1

        for campo in CAMPOS_BIEN:
            if campo["attr"] == "codigo_bien":
                continue
            valor_nuevo = getattr(fila, campo["attr"])
            if valor_nuevo is None or valor_nuevo == "":
                continue  # no borrar un dato existente con un campo vacío del staging
            setattr(bien, campo["attr"], valor_nuevo)

        # El estado de revisión (workflow TIC) de un bien YA aprobado/observado
        # nunca se toca por una fusión de datos; solo los bienes nuevos
        # arrancan en "En Revisión".

    db.session.commit()

    registrar(
        usuario=usuario,
        accion="Migración de inventario previo",
        detalle=(
            f"Insertados: {resumen.insertados}, actualizados: {resumen.actualizados}, "
            f"omitidos (no verificados): {resumen.omitidos}"
        ),
    )

    return resumen
