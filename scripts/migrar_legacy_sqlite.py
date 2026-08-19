"""Migración única de datos reales desde el SQLite del prototipo anterior
(matriz/inventario_general.db) hacia el nuevo sistema MySQL.

Qué migra:
  - `inventario` (8,510 bienes reales) -> tabla `inventario` del sistema nuevo,
    upsert por "Código del Bien" (idempotente: se puede reejecutar sin duplicar).
    Los nombres de columna coinciden 1:1 con el esquema nuevo, así que no se
    necesita mapeo de alias (eso es solo para Excels externos, ver
    app/utils/excel_import.py). La columna `estado_revision` del sistema
    viejo es la que realmente refleja el flujo de aprobación TIC (la columna
    `estado` del viejo quedó siempre en 'En Revisión' sin usarse) → se mapea
    a la columna `estado` del sistema nuevo.
  - `usuarios` (4 usuarios reales) -> se recrean con sus mismos username/rol.
    Las contraseñas NO se migran (el sistema viejo usa hash scrypt de
    Werkzeug, el nuevo usa bcrypt): se genera una contraseña temporal única
    por usuario que debe cambiarse en el primer ingreso. El usuario 'admin'
    ya existe (seed de sql/schema.sql) y se deja intacto.
  - `bitacora_auditoria` (13 eventos) -> se copian tal cual, conservando su
    fecha original, para no perder continuidad del historial.

Qué NO migra (evaluado y descartado, ver conversación): `bienes` (tabla no
relacionada con datos de prueba tipo "mesa"/"silla"), `historial_bienes` y
`historial_ubicaciones` (vacías), y el `inventario_previo` viejo (es un
espejo 1:1 de `inventario` sin información adicional).

Uso:
    cd "nuevo inventario v1"
    .venv\\Scripts\\python.exe scripts\\migrar_legacy_sqlite.py
"""
import secrets
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models.bitacora import BitacoraAuditoria
from app.models.inventario import ESTADO_APROBADO, ESTADO_EN_REVISION, ESTADOS_VALIDOS, Inventario
from app.models.usuario import Usuario
from app.utils.campos import CAMPOS_BIEN, TIPO_DECIMAL, TIPO_ENTERO, TIPO_FECHA
from app.utils.parsing import limpiar_texto, parse_decimal, parse_entero, parse_fecha

RUTA_SQLITE = Path(__file__).resolve().parent.parent / "matriz" / "inventario_general.db"

PARSERS = {
    TIPO_DECIMAL: parse_decimal,
    TIPO_ENTERO: parse_entero,
    TIPO_FECHA: parse_fecha,
}


def migrar_inventario(cur_sqlite) -> dict:
    columnas_oficiales = [c["label"] for c in CAMPOS_BIEN]
    columnas_sql = ", ".join(f'"{c}"' for c in columnas_oficiales)
    cur_sqlite.execute(f'SELECT {columnas_sql}, "Usuario Registro", estado_revision FROM inventario')
    filas = cur_sqlite.fetchall()

    codigos = [f[0] for f in filas]
    existentes = {
        b.codigo_bien: b
        for lote_inicio in range(0, len(codigos), 500)
        for b in Inventario.query.filter(
            Inventario.codigo_bien.in_(codigos[lote_inicio:lote_inicio + 500])
        ).all()
    }

    insertados = actualizados = omitidos = 0

    for fila in filas:
        valores = dict(zip(columnas_oficiales, fila[:-2]))
        usuario_registro = fila[-2]
        estado_revision_vieja = fila[-1]

        codigo_bien = limpiar_texto(valores.get("Código del Bien"))
        if not codigo_bien:
            omitidos += 1
            continue

        bien = existentes.get(codigo_bien)
        if bien is None:
            bien = Inventario(codigo_bien=codigo_bien)
            db.session.add(bien)
            existentes[codigo_bien] = bien
            insertados += 1
        else:
            actualizados += 1

        for campo in CAMPOS_BIEN:
            crudo = valores.get(campo["label"])
            parser = PARSERS.get(campo["tipo"], limpiar_texto)
            setattr(bien, campo["attr"], parser(crudo))

        bien.usuario_registro = limpiar_texto(usuario_registro) or "admin"
        bien.estado = estado_revision_vieja if estado_revision_vieja in ESTADOS_VALIDOS else ESTADO_EN_REVISION

    db.session.commit()
    return {"insertados": insertados, "actualizados": actualizados, "omitidos": omitidos}


def migrar_usuarios(cur_sqlite) -> dict:
    cur_sqlite.execute("SELECT username, rol FROM usuarios")
    filas = cur_sqlite.fetchall()

    creados = 0
    omitidos_existentes = 0
    credenciales_temporales = []

    for username, rol in filas:
        username = limpiar_texto(username)
        if not username:
            continue
        if Usuario.query.filter_by(username=username).first():
            omitidos_existentes += 1
            continue

        password_temporal = secrets.token_urlsafe(9)
        usuario = Usuario(username=username, rol=rol or "Tecnico Levantamiento", activo=True)
        usuario.set_password(password_temporal)
        db.session.add(usuario)
        creados += 1
        credenciales_temporales.append((username, rol, password_temporal))

    db.session.commit()
    return {"creados": creados, "omitidos_existentes": omitidos_existentes, "credenciales": credenciales_temporales}


def migrar_bitacora(cur_sqlite) -> dict:
    cur_sqlite.execute("SELECT codigo_bien, usuario, accion, detalle, fecha FROM bitacora_auditoria")
    filas = cur_sqlite.fetchall()

    for codigo_bien, usuario, accion, detalle, fecha in filas:
        entrada = BitacoraAuditoria(
            codigo_bien=codigo_bien,
            usuario=usuario,
            accion=f"[Histórico] {accion}" if accion else "Evento histórico",
            detalle=detalle,
        )
        if fecha:
            from datetime import datetime
            try:
                entrada.fecha = datetime.fromisoformat(fecha)
            except ValueError:
                pass
        db.session.add(entrada)

    db.session.commit()
    return {"migrados": len(filas)}


def main():
    if not RUTA_SQLITE.exists():
        print(f"ERROR: no se encontró el archivo SQLite en {RUTA_SQLITE}")
        sys.exit(1)

    conn_sqlite = sqlite3.connect(str(RUTA_SQLITE))
    cur_sqlite = conn_sqlite.cursor()

    app = create_app()
    with app.app_context():
        print("== Migrando inventario ==")
        resumen_inv = migrar_inventario(cur_sqlite)
        print(resumen_inv)

        print("== Migrando usuarios ==")
        resumen_usr = migrar_usuarios(cur_sqlite)
        print({"creados": resumen_usr["creados"], "omitidos_existentes": resumen_usr["omitidos_existentes"]})

        print("== Migrando bitácora de auditoría ==")
        resumen_bit = migrar_bitacora(cur_sqlite)
        print(resumen_bit)

    conn_sqlite.close()

    print("\n=== CREDENCIALES TEMPORALES (compártelas y pide cambiarlas al primer ingreso) ===")
    for username, rol, password in resumen_usr["credenciales"]:
        print(f"  usuario={username}  rol={rol}  password_temporal={password}")

    print("\nMigración completada.")


if __name__ == "__main__":
    main()
