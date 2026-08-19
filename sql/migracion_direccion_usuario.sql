-- =====================================================================
-- Migración: agrega la columna `direccion` a `usuarios`
-- =====================================================================
-- Úsala SOLO si ya tienes una base de datos `inamhi_inventario` creada
-- ANTES de esta funcionalidad (actas consolidadas por custodio). Si vas
-- a crear la base de datos desde cero, no hace falta: sql/schema.sql ya
-- incluye esta columna.
--
-- Es una operación segura y no destructiva: agrega una columna NULL, no
-- toca filas existentes ni las demás tablas. Ejecútala una sola vez.
-- =====================================================================

USE `inamhi_inventario`;

ALTER TABLE `usuarios`
    ADD COLUMN `direccion` VARCHAR(255) NULL AFTER `email`;
