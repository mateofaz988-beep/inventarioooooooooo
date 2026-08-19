-- =====================================================================
-- Migración: borrado lógico (soft-delete) en `inventario`
-- =====================================================================
-- Úsala SOLO si ya tienes una base de datos `inamhi_inventario` creada
-- ANTES de esta funcionalidad. Si vas a crear la base de datos desde
-- cero, no hace falta: sql/schema.sql ya incluye estas columnas.
--
-- Segura y no destructiva: agrega columnas con default 0/NULL, no borra
-- ni modifica filas existentes. Ejecútala una sola vez.
-- =====================================================================

USE `inamhi_inventario`;

ALTER TABLE `inventario`
    ADD COLUMN `eliminado`         TINYINT(1) NOT NULL DEFAULT 0 AFTER `revisado_por_tic`,
    ADD COLUMN `fecha_eliminacion` DATETIME   NULL     AFTER `eliminado`,
    ADD COLUMN `eliminado_por`     VARCHAR(80) NULL    AFTER `fecha_eliminacion`,
    ADD KEY `ix_inventario_eliminado` (`eliminado`);
