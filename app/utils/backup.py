"""Respaldo automático de la base de datos MySQL vía `mysqldump` (subprocess).

Guarda archivos con timestamp en BACKUP_DIR y conserva solo los últimos
BACKUP_KEEP respaldos (borra los más antiguos).
"""
import os
import subprocess
from datetime import datetime
from pathlib import Path


class RespaldoError(Exception):
    pass


def generar_respaldo(config) -> Path:
    """`config` es un mapping estilo `app.config` de Flask (acceso por clave,
    no por atributo) — así es como se invoca normalmente, dentro de un
    app_context: `generar_respaldo(current_app.config)`.
    """
    carpeta = Path(config["BACKUP_DIR"])
    carpeta.mkdir(parents=True, exist_ok=True)

    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_destino = carpeta / f"inamhi_inventario_{marca_tiempo}.sql"

    mysqldump_path = config["MYSQLDUMP_PATH"]
    comando = [
        mysqldump_path,
        f"--host={config['DB_HOST']}",
        f"--port={config['DB_PORT']}",
        f"--user={config['DB_USER']}",
        f"--password={config['DB_PASSWORD']}",
        "--single-transaction",
        "--routines",
        "--triggers",
        "--default-character-set=utf8mb4",
        config["DB_NAME"],
    ]

    try:
        with open(archivo_destino, "wb") as salida:
            resultado = subprocess.run(comando, stdout=salida, stderr=subprocess.PIPE, check=False)
    except FileNotFoundError as exc:
        raise RespaldoError(
            f"No se encontró el ejecutable '{mysqldump_path}'. Verifica que MySQL "
            f"client tools estén instalados y en el PATH, o configura MYSQLDUMP_PATH en .env."
        ) from exc

    if resultado.returncode != 0:
        archivo_destino.unlink(missing_ok=True)
        raise RespaldoError(f"mysqldump falló: {resultado.stderr.decode('utf-8', errors='replace')}")

    _purgar_respaldos_antiguos(carpeta, config["BACKUP_KEEP"])
    return archivo_destino


def _purgar_respaldos_antiguos(carpeta: Path, conservar: int) -> None:
    respaldos = sorted(carpeta.glob("inamhi_inventario_*.sql"), key=os.path.getmtime, reverse=True)
    for respaldo_viejo in respaldos[conservar:]:
        respaldo_viejo.unlink(missing_ok=True)
