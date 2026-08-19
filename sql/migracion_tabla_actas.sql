-- =====================================================================
-- Migración: tabla `actas` (historial inmutable + numeración correlativa)
-- =====================================================================
-- Úsala SOLO si ya tienes una base de datos `inamhi_inventario` creada
-- ANTES de esta funcionalidad. Si vas a crear la base de datos desde
-- cero, no hace falta: sql/schema.sql ya incluye esta tabla.
--
-- No toca ninguna tabla existente, solo crea una nueva. Ejecútala una
-- sola vez.
-- =====================================================================

USE `inamhi_inventario`;

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
