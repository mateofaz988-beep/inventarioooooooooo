from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models.bien_historial_custodio import BienHistorialCustodio
from app.models.inventario import ESTADO_APROBADO, ESTADO_EN_REVISION, Inventario
from app.utils.auditoria import registrar
from app.utils.busqueda import aplicar_busqueda_texto
from app.utils.campos import (
    CAMPOS_BIEN, CAMPOS_POR_ATTR, CAMPOS_REQUERIDOS, TIPO_DECIMAL, TIPO_ENTERO, TIPO_FECHA, TIPO_TEXTO,
)
from app.utils.parsing import limpiar_texto_corto, parse_decimal, parse_entero, parse_fecha
from app.utils.permisos import campos_bloqueados_para, puede_editar_bien
from app.api.decorators import admin_required_api, usuario_desde_jwt

api_bienes_bp = Blueprint("api_bienes", __name__, url_prefix="/api/bienes")


def _aplicar_campos_json(
    bien: Inventario, datos: dict, incluir_codigo: bool = False, campos_bloqueados: frozenset = frozenset()
) -> None:
    for campo in CAMPOS_BIEN:
        if campo["attr"] == "codigo_bien" and not incluir_codigo:
            continue
        if campo["attr"] in campos_bloqueados:
            continue
        if campo["attr"] not in datos:
            continue
        crudo = datos.get(campo["attr"])
        if campo["tipo"] == TIPO_DECIMAL:
            valor = parse_decimal(crudo)
        elif campo["tipo"] == TIPO_ENTERO:
            valor = parse_entero(crudo)
        elif campo["tipo"] == TIPO_FECHA:
            valor = parse_fecha(crudo)
        elif campo["tipo"] == TIPO_TEXTO:
            valor = limpiar_texto_corto(crudo)
        else:
            valor = (str(crudo).strip() or None) if crudo is not None else None
        setattr(bien, campo["attr"], valor)


@api_bienes_bp.route("", methods=["GET"])
@jwt_required()
def listar():
    termino = (request.args.get("q") or "").strip()
    estado = (request.args.get("estado") or "").strip()
    pagina = request.args.get("pagina", 1, type=int)
    por_pagina = min(request.args.get("por_pagina", 10, type=int), 100)

    consulta = Inventario.query.filter(Inventario.eliminado.is_(False))
    if termino:
        consulta = aplicar_busqueda_texto(consulta, termino)
    if estado:
        consulta = consulta.filter_by(estado=estado)

    total = consulta.count()
    bienes = (
        consulta.order_by(Inventario.id.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )

    return jsonify({
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "resultados": [b.to_dict() for b in bienes],
    }), 200


@api_bienes_bp.route("", methods=["POST"])
@jwt_required()
def crear():
    usuario = usuario_desde_jwt()
    datos = request.get_json(silent=True) or {}
    codigo_bien = (datos.get("codigo_bien") or "").strip()

    if not codigo_bien:
        return jsonify({"error": "codigo_bien es obligatorio"}), 400

    # Mismo criterio que la ruta web equivalente (ver app/web/inventario.py:nuevo):
    # un bien creado aquí nace en estado "En Revisión", así que debe cumplir la
    # misma validación de campos obligatorios que exige editar()/PUT para ese estado.
    faltantes = [
        CAMPOS_POR_ATTR[attr]["label"]
        for attr in CAMPOS_REQUERIDOS
        if attr != "codigo_bien" and not str(datos.get(attr) or "").strip()
    ]
    if faltantes:
        return jsonify({"error": "Faltan campos obligatorios", "campos": faltantes}), 400

    if Inventario.query.filter_by(codigo_bien=codigo_bien).first():
        return jsonify({"error": f"Ya existe un bien con el código '{codigo_bien}'"}), 409

    bien = Inventario(codigo_bien=codigo_bien, estado=ESTADO_EN_REVISION, usuario_registro=usuario.username)
    _aplicar_campos_json(bien, datos, campos_bloqueados=campos_bloqueados_para(usuario))
    db.session.add(bien)
    db.session.commit()

    registrar(usuario=usuario.username, accion="Creación de bien (API)", codigo_bien=codigo_bien)

    return jsonify(bien.to_dict()), 201


@api_bienes_bp.route("/<codigo>", methods=["GET"])
@jwt_required()
def obtener(codigo):
    bien = Inventario.query.filter_by(codigo_bien=codigo, eliminado=False).first()
    if bien is None:
        return jsonify({"error": "Bien no encontrado"}), 404
    return jsonify(bien.to_dict()), 200


@api_bienes_bp.route("/<codigo>", methods=["PUT", "PATCH"])
@jwt_required()
def editar(codigo):
    usuario = usuario_desde_jwt()
    bien = Inventario.query.filter_by(codigo_bien=codigo, eliminado=False).first()
    if bien is None:
        return jsonify({"error": "Bien no encontrado"}), 404

    if not puede_editar_bien(usuario, bien):
        return jsonify({"error": "Acceso denegado para editar este bien"}), 403

    datos = request.get_json(silent=True) or {}
    estado_revision = (datos.get("estado_revision") or "").strip() or bien.estado

    if estado_revision == ESTADO_EN_REVISION:
        faltantes = [
            CAMPOS_POR_ATTR[attr]["label"]
            for attr in CAMPOS_REQUERIDOS
            if not str(datos.get(attr, getattr(bien, attr) or "")).strip()
        ]
        if faltantes:
            return jsonify({"error": "Faltan campos obligatorios", "campos": faltantes}), 400

    custodio_anterior = bien.custodio_actual
    _aplicar_campos_json(bien, datos, campos_bloqueados=campos_bloqueados_para(usuario))
    bien.estado = estado_revision

    if bien.custodio_actual != custodio_anterior:
        db.session.add(BienHistorialCustodio(
            codigo_bien=bien.codigo_bien, custodio_anterior=custodio_anterior,
            custodio_nuevo=bien.custodio_actual, usuario_modifica=usuario.username,
        ))

    db.session.commit()

    registrar(usuario=usuario.username, accion="Edición de bien (API)", codigo_bien=codigo)

    return jsonify(bien.to_dict()), 200


@api_bienes_bp.route("/<codigo>", methods=["DELETE"])
@admin_required_api
def eliminar(codigo):
    usuario = usuario_desde_jwt()
    bien = Inventario.query.filter_by(codigo_bien=codigo, eliminado=False).first()
    if bien is None:
        return jsonify({"error": "Bien no encontrado"}), 404

    # Borrado lógico, igual que la ruta web equivalente (ver
    # app/web/inventario.py:eliminar) — nunca DELETE físico.
    bien.eliminado = True
    bien.fecha_eliminacion = datetime.utcnow()
    bien.eliminado_por = usuario.username
    db.session.commit()

    registrar(usuario=usuario.username, accion="Eliminación de bien (API)", codigo_bien=codigo)

    return jsonify({"mensaje": f"Bien '{codigo}' eliminado"}), 200
