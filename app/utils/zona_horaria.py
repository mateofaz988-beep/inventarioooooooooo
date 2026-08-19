"""Conversión de fechas guardadas en UTC a la hora local de Ecuador.

Todos los timestamps (`datetime.utcnow`) se guardan en UTC en la base de
datos -eso no cambia-, pero se deben mostrar en hora de Ecuador
(UTC-5 todo el año, sin horario de verano) en las páginas HTML.
"""
from datetime import datetime, timedelta, timezone

ZONA_ECUADOR = timezone(timedelta(hours=-5), name="ECT")


def hora_ecuador(valor: datetime | None, formato: str = "%Y-%m-%d %H:%M:%S") -> str:
    if valor is None:
        return "-"
    local = valor.replace(tzinfo=timezone.utc).astimezone(ZONA_ECUADOR)
    return local.strftime(formato)
