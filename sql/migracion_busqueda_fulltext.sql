-- =====================================================================
-- Migración: índice FULLTEXT para la búsqueda libre de /inventario
-- =====================================================================
-- Úsala SOLO si ya tienes una base de datos `inamhi_inventario` creada
-- ANTES de esta funcionalidad. Si vas a crear la base de datos desde
-- cero, no hace falta: sql/schema.sql ya incluye este índice.
--
-- La búsqueda libre anterior hacía OR ILIKE('%término%') sobre 13
-- columnas: con un wildcard al inicio ningún índice B-tree puede usarse,
-- así que cada búsqueda es un full table scan. Un índice FULLTEXT +
-- MATCH()...AGAINST() sí usa índice.
--
-- Requiere InnoDB (ya lo es) y MySQL 5.6+/8.x. Puede tardar unos segundos
-- en tablas grandes porque reconstruye el índice.
-- =====================================================================

USE `inamhi_inventario`;

ALTER TABLE `inventario`
    ADD FULLTEXT KEY `ftx_inventario_texto_libre` (
        `Bien`, `Serie/ Identificación`, `Modelo/ Características`,
        `Marca/ Otros`, `Descripción`, `Custodio Actual`, `Ubicación de Bodega`
    );
