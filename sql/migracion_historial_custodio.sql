-- =====================================================================
-- Migración: tabla `bien_historial_custodio` (trazabilidad de traspasos)
-- =====================================================================
-- Úsala SOLO si ya tienes una base de datos `inamhi_inventario` creada
-- ANTES de esta funcionalidad. Si vas a crear la base de datos desde
-- cero, no hace falta: sql/schema.sql ya incluye esta tabla.
--
-- No toca ninguna tabla existente, solo crea una nueva. Ejecútala una
-- sola vez.
-- =====================================================================

USE `inamhi_inventario`;

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
