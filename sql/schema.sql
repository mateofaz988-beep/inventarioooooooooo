-- =====================================================================
-- INAMHI | Control de Activos - Script de creación de base de datos
-- Motor: MySQL 8.x - Ejecutar completo en MySQL Workbench
-- =====================================================================
-- Contiene: creación de la base, las 4 tablas del sistema con sus
-- índices, y el usuario administrador inicial (contraseña ya cifrada
-- con bcrypt, documentada en README.md).
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `inamhi_inventario`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `inamhi_inventario`;

-- ---------------------------------------------------------------------
-- Tabla: usuarios
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `usuarios` (
    `id`               INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    `username`         VARCHAR(80)     NOT NULL,
    `password_hash`    VARCHAR(255)    NOT NULL,
    `rol`              VARCHAR(50)     NOT NULL DEFAULT 'Tecnico Levantamiento',
    `nombre_completo`  VARCHAR(150)    NULL,
    `email`            VARCHAR(150)    NULL,
    `direccion`        VARCHAR(255)    NULL,
    `activo`           TINYINT(1)      NOT NULL DEFAULT 1,
    `fecha_creacion`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_usuarios_username` (`username`),
    KEY `ix_usuarios_rol` (`rol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Tabla: inventario
-- Nombres de columna EXACTOS en español (con tildes/paréntesis), tal
-- como los usa la institución. No traducir ni renombrar.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `inventario` (
    `id`                              INT UNSIGNED    NOT NULL AUTO_INCREMENT,

    -- Identificación
    `Código del Bien`                 VARCHAR(255)    NOT NULL,
    `Código Anterior`                 VARCHAR(255)    NULL,
    `Identificador`                   VARCHAR(255)    NULL,
    `Nro de Acta/ Nro de Matriz`      VARCHAR(255)    NULL,
    `(BLD) o (BCA)`                   VARCHAR(255)    NULL,
    `Bien`                            VARCHAR(255)    NULL,
    `Serie/ Identificación`           VARCHAR(255)    NULL,
    `Modelo/ Características`        TEXT            NULL,
    `Marca/ Otros`                    VARCHAR(255)    NULL,
    `Crítico`                         VARCHAR(255)    NULL,
    `Descripción`                     TEXT            NULL,

    -- Valoración
    `Moneda`                          VARCHAR(255)    NULL,
    `Valor de Compra`                 DECIMAL(14,2)   NULL,
    `Recompra`                        VARCHAR(255)    NULL,
    `Valor Contable`                  DECIMAL(14,2)   NULL,
    `Valor Residual`                  DECIMAL(14,2)   NULL,
    `Valor en Libros`                 DECIMAL(14,2)   NULL,
    `Valor Depreciación Acumulada`    DECIMAL(14,2)   NULL,
    `Cuenta Contable`                 VARCHAR(255)    NULL,
    `Depreciable`                     VARCHAR(255)    NULL,
    `Vida Útil`                       INT             NULL,
    `Fecha Última Depreciación`       DATE            NULL,
    `Fecha Término Depreciación`      DATE            NULL,

    -- Características y condición
    `Color`                           VARCHAR(255)    NULL,
    `Material`                        VARCHAR(255)    NULL,
    `Dimensiones`                     TEXT            NULL,
    `Condición del Bien`              VARCHAR(255)    NULL,
    `Habilitado`                      VARCHAR(255)    NULL,
    `Estado Bien`                     VARCHAR(255)    NULL,
    `Comodato`                        VARCHAR(255)    NULL,
    `Item/ Renglón`                   VARCHAR(255)    NULL,

    -- Ubicación, custodia y actas
    `Id Bodega`                       VARCHAR(255)    NULL,
    `Bodega`                          VARCHAR(255)    NULL,
    `Id Ubicación`                    VARCHAR(255)    NULL,
    `Ubicación de Bodega`             VARCHAR(255)    NULL,
    `Nro de Cédula/ RUC`              VARCHAR(255)    NULL,
    `Custodio Actual`                 VARCHAR(255)    NULL,
    `Custodio Activo`                 VARCHAR(255)    NULL,
    `Origen del Ingreso`              VARCHAR(255)    NULL,
    `Tipo de Ingreso`                 VARCHAR(255)    NULL,
    `Nro de Compromiso`               VARCHAR(255)    NULL,
    `Estado del Acta`                 VARCHAR(255)    NULL,
    `Contabilizado del Acta`          VARCHAR(255)    NULL,
    `Contabilizado del Bien`          VARCHAR(255)    NULL,
    `Fecha de Creación`               DATE            NULL,
    `Fecha de Ingreso`                DATE            NULL,

    -- Flujo de trabajo (control interno, no proviene del Excel)
    `Usuario Registro`                VARCHAR(80)     NULL,
    `estado`                          VARCHAR(50)     NOT NULL DEFAULT 'En Revisión',
    `observaciones_tic`               TEXT            NULL,
    `fecha_revision_tic`              DATETIME        NULL,
    `revisado_por_tic`                VARCHAR(80)     NULL,

    -- Borrado lógico: "Eliminar" nunca hace DELETE físico (ver comentario en
    -- app/models/inventario.py). Todas las consultas de listado deben
    -- filtrar `eliminado` = 0.
    `eliminado`                       TINYINT(1)      NOT NULL DEFAULT 0,
    `fecha_eliminacion`               DATETIME        NULL,
    `eliminado_por`                   VARCHAR(80)     NULL,

    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_inventario_codigo_bien` (`Código del Bien`),
    KEY `ix_inventario_bien` (`Bien`),
    KEY `ix_inventario_estado_bien` (`Estado Bien`),
    KEY `ix_inventario_custodio_actual` (`Custodio Actual`),
    KEY `ix_inventario_usuario_registro` (`Usuario Registro`),
    KEY `ix_inventario_estado` (`estado`),
    KEY `ix_inventario_eliminado` (`eliminado`),
    FULLTEXT KEY `ftx_inventario_texto_libre` (
        `Bien`, `Serie/ Identificación`, `Modelo/ Características`,
        `Marca/ Otros`, `Descripción`, `Custodio Actual`, `Ubicación de Bodega`
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Tabla: inventario_previo (staging de cargas Excel)
-- Tiene una columna por cada campo oficial de `inventario` (mismos nombres
-- de atributo Python, en snake_case aquí ya que es una tabla de control
-- interno, no la tabla "oficial"), para no perder información rica del
-- Excel entre la carga y la migración/fusión hacia el inventario oficial.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `inventario_previo` (
    `id`                              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    `codigo_bien`                     VARCHAR(255)    NOT NULL,
    `codigo_generado`                 TINYINT(1)      NOT NULL DEFAULT 0,

    `codigo_anterior`                 VARCHAR(255)    NULL,
    `identificador`                   VARCHAR(255)    NULL,
    `nro_acta_matriz`                 VARCHAR(255)    NULL,
    `bld_o_bca`                       VARCHAR(255)    NULL,
    `bien`                            VARCHAR(255)    NULL,
    `serie_identificacion`            VARCHAR(255)    NULL,
    `modelo_caracteristicas`          TEXT            NULL,
    `marca_otros`                     VARCHAR(255)    NULL,
    `critico`                         VARCHAR(255)    NULL,
    `descripcion`                     TEXT            NULL,

    `moneda`                          VARCHAR(255)    NULL,
    `valor_compra`                    DECIMAL(14,2)   NULL,
    `recompra`                        VARCHAR(255)    NULL,
    `valor_contable`                  DECIMAL(14,2)   NULL,
    `valor_residual`                  DECIMAL(14,2)   NULL,
    `valor_en_libros`                 DECIMAL(14,2)   NULL,
    `valor_depreciacion_acumulada`    DECIMAL(14,2)   NULL,
    `cuenta_contable`                 VARCHAR(255)    NULL,
    `depreciable`                     VARCHAR(255)    NULL,
    `vida_util`                       INT             NULL,
    `fecha_ultima_depreciacion`       DATE            NULL,
    `fecha_termino_depreciacion`      DATE            NULL,

    `color`                           VARCHAR(255)    NULL,
    `material`                        VARCHAR(255)    NULL,
    `dimensiones`                     TEXT            NULL,
    `condicion_bien`                  VARCHAR(255)    NULL,
    `habilitado`                      VARCHAR(255)    NULL,
    `estado_bien`                     VARCHAR(255)    NULL,
    `comodato`                        VARCHAR(255)    NULL,
    `item_renglon`                    VARCHAR(255)    NULL,

    `id_bodega`                       VARCHAR(255)    NULL,
    `bodega`                          VARCHAR(255)    NULL,
    `id_ubicacion`                    VARCHAR(255)    NULL,
    `ubicacion_bodega`                VARCHAR(255)    NULL,
    `nro_cedula_ruc`                  VARCHAR(255)    NULL,
    `custodio_actual`                 VARCHAR(255)    NULL,
    `custodio_activo`                 VARCHAR(255)    NULL,
    `origen_ingreso`                  VARCHAR(255)    NULL,
    `tipo_ingreso`                    VARCHAR(255)    NULL,
    `nro_compromiso`                  VARCHAR(255)    NULL,
    `estado_acta`                     VARCHAR(255)    NULL,
    `contabilizado_acta`              VARCHAR(255)    NULL,
    `contabilizado_bien`              VARCHAR(255)    NULL,
    `fecha_creacion`                  DATE            NULL,
    `fecha_ingreso`                   DATE            NULL,

    `observaciones_carga`             TEXT            NULL,
    `nombre_archivo_origen`           VARCHAR(255)    NULL,
    `fecha_carga`                     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `verificado`                      TINYINT(1)      NOT NULL DEFAULT 0,
    `usuario_verificador`             VARCHAR(80)     NULL,

    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_inventario_previo_codigo` (`codigo_bien`),
    KEY `ix_inventario_previo_verificado` (`verificado`),
    KEY `ix_inventario_previo_bien` (`bien`),
    KEY `ix_inventario_previo_estado_bien` (`estado_bien`),
    KEY `ix_inventario_previo_ubicacion` (`ubicacion_bodega`),
    KEY `ix_inventario_previo_custodio` (`custodio_actual`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Tabla: actas
-- Registro inmutable de cada acta consolidada emitida. `id` funciona
-- directamente como el número de acta correlativo (AUTO_INCREMENT nativo,
-- sin condición de carrera). `bienes_snapshot` guarda los bienes TAL COMO
-- ESTABAN al emitirse el acta, no una referencia viva a `inventario`, para
-- que reimprimir siempre muestre lo que se firmó originalmente.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `actas` (
    `id`                    INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    `custodio`              VARCHAR(255)    NOT NULL,
    `usuario_elabora`       VARCHAR(80)     NOT NULL,
    `elaborado_nombre`      VARCHAR(150)    NULL,
    `elaborado_direccion`   VARCHAR(255)    NULL,
    `fecha_emision`         DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `total_bienes`          INT             NOT NULL,
    `total_valor`           DECIMAL(14,2)   NOT NULL,
    `bienes_snapshot`       JSON            NOT NULL,
    PRIMARY KEY (`id`),
    KEY `ix_actas_custodio` (`custodio`),
    KEY `ix_actas_fecha_emision` (`fecha_emision`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Tabla: bien_historial_custodio
-- Traza cada cambio de custodio de un bien. Sin FK hacia `inventario` a
-- propósito (mismo criterio que `bitacora_auditoria`): debe sobrevivir a
-- que el bien se elimine (borrado lógico) o cambie de código.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `bien_historial_custodio` (
    `id`                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    `codigo_bien`         VARCHAR(255)    NOT NULL,
    `custodio_anterior`   VARCHAR(255)    NULL,
    `custodio_nuevo`      VARCHAR(255)    NULL,
    `usuario_modifica`    VARCHAR(80)     NULL,
    `fecha_traspaso`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `ix_historial_custodio_codigo_bien` (`codigo_bien`),
    KEY `ix_historial_custodio_fecha` (`fecha_traspaso`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Tabla: bitacora_auditoria
-- Sin FK hacia inventario/usuarios a propósito: son snapshots de texto
-- histórico y el sistema audita después de eliminar un bien o puede
-- referenciar usuarios ya eliminados.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `bitacora_auditoria` (
    `id`            INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    `codigo_bien`   VARCHAR(255)    NULL,
    `usuario`       VARCHAR(80)     NULL,
    `accion`        VARCHAR(100)    NOT NULL,
    `detalle`       TEXT            NULL,
    `fecha`         DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `ix_bitacora_codigo_bien` (`codigo_bien`),
    KEY `ix_bitacora_usuario` (`usuario`),
    KEY `ix_bitacora_accion` (`accion`),
    KEY `ix_bitacora_fecha` (`fecha`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Usuario administrador inicial
-- Usuario:    admin
-- Contraseña: Inamhi2026*   (CAMBIARLA inmediatamente después del primer
--             ingreso, desde Gestión de Usuarios -> Cambiar contraseña)
-- El hash fue generado con bcrypt (12 rondas) y es compatible con
-- Flask-Bcrypt (usado tanto por el login de páginas como por /api/auth/login).
-- ---------------------------------------------------------------------
INSERT INTO `usuarios` (`username`, `password_hash`, `rol`, `nombre_completo`, `email`, `activo`)
VALUES (
    'admin',
    '$2b$12$riNACU6F.l3Hs7bWZpzZkuF/H2BINskJEF7tc4kGNtUfcgnZ.oxQi',
    'Administrador',
    'Administrador del Sistema',
    'admin@inamhi.gob.ec',
    1
)
ON DUPLICATE KEY UPDATE `username` = `username`;
