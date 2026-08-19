"""Parseo tolerante a errores para datos que vienen de Excel o de formularios HTML.

Regla de oro: un valor que no se puede interpretar como fecha/número válido se
guarda como NULL. Nunca se lanza una excepción por un dato sucio y nunca se
inventa un valor — los datos históricos de este tipo de institución traen
errores de captura (fechas imposibles, texto en campos numéricos, etc.).
"""
import math
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pandas as pd


def limpiar_texto(valor) -> str | None:
    if valor is None:
        return None
    if isinstance(valor, float) and math.isnan(valor):
        return None
    texto = str(valor).strip()
    if texto == "" or texto.lower() in {"nan", "none", "nat"}:
        return None
    return texto


def limpiar_texto_corto(valor, max_len: int = 255) -> str | None:
    """Como limpiar_texto, pero recorta a max_len caracteres.

    Red de seguridad para columnas VARCHAR(255): datos institucionales reales
    a veces traen una descripción larga en un campo pensado para un valor
    corto (p.ej. una ficha técnica completa en "Dimensiones"). Preferimos
    recortar el texto a fallar toda la carga por una sola fila.
    """
    texto = limpiar_texto(valor)
    if texto is None:
        return None
    if len(texto) > max_len:
        return texto[:max_len]
    return texto


def parse_fecha(valor) -> date | None:
    if valor is None:
        return None
    if isinstance(valor, float) and math.isnan(valor):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "none", "nat"}:
        return None
    try:
        parsed = pd.to_datetime(texto, dayfirst=True, errors="coerce")
    except (ValueError, TypeError):
        return None
    if parsed is None or pd.isna(parsed):
        return None
    return parsed.date()


def parse_decimal(valor) -> Decimal | None:
    if valor is None:
        return None
    if isinstance(valor, float) and math.isnan(valor):
        return None
    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "none"}:
        return None
    texto = texto.replace("$", "").replace(" ", "")
    # Soporta tanto "1.234,56" (formato latino) como "1234.56"
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        return Decimal(texto)
    except (InvalidOperation, ValueError):
        return None


def parse_entero(valor) -> int | None:
    if valor is None:
        return None
    if isinstance(valor, float) and math.isnan(valor):
        return None
    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "none"}:
        return None
    try:
        return int(float(texto))
    except (ValueError, TypeError):
        return None


def contar_campos_llenos(fila: dict) -> int:
    """Cuenta cuántos valores no vacíos tiene una fila (dict de atributo -> valor)."""
    total = 0
    for valor in fila.values():
        if valor is None:
            continue
        if isinstance(valor, str) and valor.strip() == "":
            continue
        total += 1
    return total


# Valores centinela que instituciones como esta usan como texto literal en la
# celda de código para decir "todavía no tiene código oficial asignado" (en
# vez de dejar la celda vacía). Si no se filtran, cientos de bienes distintos
# terminarían compartiendo el mismo "código" y se fusionarían en uno solo.
# Lista abierta a extender: cualquier matriz nueva puede traer un placeholder
# distinto.
PLACEHOLDERS_CODIGO = {
    "INGRESAR", "DEFINIR", "POR DEFINIR", "POR ASIGNAR", "POR INGRESAR",
    "SIN CODIGO", "SIN CÓDIGO", "SIN CODIGO ESBYE", "SIN CÓDIGO ESBYE",
    "SIN CODIGO ESBYE", "N/A", "NA", "S/N", "SIN CODIGO ASIGNADO",
    "PENDIENTE", "-", "--",
}


def limpiar_codigo(valor) -> str | None:
    """Como limpiar_texto, pero además descarta valores centinela tipo
    'SIN CODIGO ESBYE' o 'INGRESAR' que no son códigos reales."""
    texto = limpiar_texto(valor)
    if texto is None:
        return None
    if texto.strip().upper() in PLACEHOLDERS_CODIGO:
        return None
    return texto
