"""Búsqueda libre de `Inventario`, dividida en dos estrategias según el tipo
de columna:

- Columnas "de texto libre" (Bien, Serie, Modelo, Marca, Descripción,
  Custodio Actual, Ubicación de Bodega): usan el índice FULLTEXT
  `ftx_inventario_texto_libre` vía MATCH()...AGAINST(), que sí puede usar
  índice. La búsqueda anterior hacía OR ILIKE('%término%') sobre estas
  mismas columnas de texto largo — con wildcard al inicio, invalida
  cualquier índice y fuerza un full table scan en cada búsqueda.
- Columnas "tipo código/identificador" (código, estado, bodega, usuario,
  cédula/RUC): son cortas y no se benefician de FULLTEXT (además, tokens de
  menos de `innodb_ft_min_token_size` -3 por defecto- ni siquiera se indexan
  ahí), así que se quedan en ILIKE, pero sobre un conjunto de columnas mucho
  más chico que antes (8 en vez de 13).

Nota operativa: si en el futuro se necesita buscar por marcas/códigos muy
cortos (2 caracteres) dentro de las columnas FULLTEXT y no aparecen
resultados, es por `innodb_ft_min_token_size` (requiere ajustar la variable
de MySQL + reconstruir el índice, no es algo que la app pueda resolver sola).
"""
import re

from sqlalchemy import text

from app.extensions import db
from app.models.inventario import Inventario

COLUMNAS_FULLTEXT_SQL = (
    "`Bien`, `Serie/ Identificación`, `Modelo/ Características`, "
    "`Marca/ Otros`, `Descripción`, `Custodio Actual`, `Ubicación de Bodega`"
)

_PATRON_PALABRA = re.compile(r"[\wÀ-ſ]+", re.UNICODE)


def _consulta_booleana(termino: str) -> str | None:
    """Convierte el término libre del usuario en una consulta BOOLEAN MODE de
    MySQL: cada palabra de 2+ caracteres se vuelve obligatoria y con
    coincidencia de prefijo (`+palabra*`), para acercarse a la UX de
    substring que tenía el ILIKE anterior. Devuelve None si no queda ninguna
    palabra utilizable (evita mandar una consulta BOOLEAN MODE vacía, que
    MySQL rechaza con error)."""
    palabras = [p for p in _PATRON_PALABRA.findall(termino) if len(p) >= 2]
    if not palabras:
        return None
    return " ".join(f'+{p}*' for p in palabras)


def aplicar_busqueda_texto(consulta, termino: str):
    """Agrega el filtro de búsqueda libre a una consulta de `Inventario`."""
    from sqlalchemy import or_

    patron = f"%{termino}%"
    filtro_ilike = or_(
        Inventario.codigo_bien.ilike(patron),
        Inventario.codigo_anterior.ilike(patron),
        Inventario.identificador.ilike(patron),
        Inventario.estado_bien.ilike(patron),
        Inventario.bodega.ilike(patron),
        Inventario.custodio_activo.ilike(patron),
        Inventario.nro_cedula_ruc.ilike(patron),
        Inventario.usuario_registro.ilike(patron),
    )

    # El índice FULLTEXT es específico de MySQL: en cualquier otro dialecto
    # (ej. SQLite en pruebas automatizadas) MATCH()...AGAINST() no existe, así
    # que se cae de vuelta a ILIKE también sobre las columnas de texto libre
    # -- correcto funcionalmente, solo pierde la ventaja de índice, que de
    # todas formas SQLite no tiene para este caso.
    es_mysql = db.session.get_bind().dialect.name == "mysql"
    consulta_booleana = _consulta_booleana(termino) if es_mysql else None

    if consulta_booleana is None:
        filtro_texto_libre = or_(
            Inventario.bien.ilike(patron),
            Inventario.serie_identificacion.ilike(patron),
            Inventario.modelo_caracteristicas.ilike(patron),
            Inventario.marca_otros.ilike(patron),
            Inventario.descripcion.ilike(patron),
            Inventario.custodio_actual.ilike(patron),
            Inventario.ubicacion_bodega.ilike(patron),
        )
        return consulta.filter(or_(filtro_ilike, filtro_texto_libre))

    filtro_fulltext = text(
        f"MATCH({COLUMNAS_FULLTEXT_SQL}) AGAINST (:termino_fulltext IN BOOLEAN MODE)"
    ).bindparams(termino_fulltext=consulta_booleana)

    return consulta.filter(or_(filtro_ilike, filtro_fulltext))
