# INAMHI | Control de Activos

Sistema institucional de control de activos / inventario de bienes. Backend en
Python (Flask + SQLAlchemy) con base de datos MySQL real, autenticación por
sesión para las páginas HTML y una capa de API JSON independiente con JWT.

## 1. Estructura del proyecto

```
nuevo inventario v1/
├── app/
│   ├── config.py            # Configuración vía variables de entorno
│   ├── extensions.py        # Instancias de SQLAlchemy, Bcrypt, JWT, CORS
│   ├── models/               # Usuario, Inventario, InventarioPrevio, BitacoraAuditoria
│   ├── web/                  # Blueprints de páginas HTML (Jinja2 + sesión)
│   ├── api/                  # Blueprints de API JSON (JWT) bajo /api/
│   ├── utils/                 # Permisos, auditoría, import/export Excel, PDF+QR, backup
│   └── templates/            # 8 páginas + base.html + macros
├── sql/schema.sql            # Script completo para MySQL Workbench
├── respaldos/                 # Carpeta destino de los backups (mysqldump)
├── requirements.txt
├── .env.example
├── run.py
└── README.md
```

## 2. Requisitos previos

- Python 3.11 o superior
- MySQL Server 8.x + MySQL Workbench
- Cliente `mysqldump` disponible (para los respaldos automáticos)

## 3. Crear la base de datos (MySQL Workbench)

1. Abre MySQL Workbench y conéctate a tu servidor con un usuario con permisos de administración (ej. `root`).
2. Crea un usuario dedicado para la aplicación (recomendado, en vez de usar `root`):

   ```sql
   CREATE USER 'inamhi_app'@'localhost' IDENTIFIED BY 'una-contrasena-segura';
   ```

3. Abre el archivo [`sql/schema.sql`](sql/schema.sql) en una nueva pestaña SQL de Workbench y ejecútalo completo (rayo ⚡ "Execute"). Esto crea:
   - La base `inamhi_inventario` (charset `utf8mb4`).
   - Las 4 tablas: `usuarios`, `inventario`, `inventario_previo`, `bitacora_auditoria`.
   - El usuario administrador inicial (ver credenciales abajo).

4. Otorga permisos al usuario dedicado sobre la base recién creada:

   ```sql
   GRANT ALL PRIVILEGES ON inamhi_inventario.* TO 'inamhi_app'@'localhost';
   FLUSH PRIVILEGES;
   ```

> **Nota sobre tildes/ñ:** ejecuta el script desde la pestaña SQL de **Workbench**
> (como se indica arriba), no desde `mysql.exe` en una consola de Windows sin
> configurar. Workbench lee el archivo como UTF-8 correctamente. Si en algún
> caso prefieres la línea de comandos, fuerza UTF-8 primero:
> `chcp 65001` y luego `mysql --default-character-set=utf8mb4 -u root -p < sql/schema.sql`;
> de lo contrario la consola de Windows puede reinterpretar los acentos con
> la página de códigos OEM y corromper los nombres de columna al insertarlos.

### Credenciales iniciales del sistema

| Usuario | Contraseña     | Rol            |
|---------|----------------|----------------|
| `admin` | `Inamhi2026*`  | Administrador  |

**Cambia esta contraseña inmediatamente** después del primer ingreso, desde
`Usuarios -> Cambiar contraseña`. El hash guardado en `sql/schema.sql` es
bcrypt real (12 rondas); en ningún lugar del sistema se guardan contraseñas
en texto plano.

## 4. Configurar el backend

1. Copia `.env.example` a `.env`:

   ```bash
   cp .env.example .env
   ```

2. Edita `.env` y ajusta como mínimo:
   - `DB_USER` / `DB_PASSWORD` / `DB_NAME` (el usuario y base creados en el paso 3).
   - `SECRET_KEY` y `JWT_SECRET_KEY`: genera valores aleatorios distintos entre sí, por ejemplo:

     ```bash
     python -c "import secrets; print(secrets.token_hex(32))"
     ```

## 5. Instalar dependencias y levantar el servidor

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt

python run.py
```

El servidor queda disponible en `http://localhost:5000`. Se redirige
automáticamente a `/login`.

## 6. Probar que todo funciona

### 6.1 Login por la web

1. Ingresa a `http://localhost:5000/login`.
2. Usuario `admin`, contraseña `Inamhi2026*`.
3. Deberías llegar a `/inventario` con la tabla vacía y el botón "Nuevo Registro".

### 6.2 Crear un bien de prueba

Desde `/inventario`, botón "Nuevo Registro" → completa "Código del Bien" y
"Bien" → Guardar. El bien queda creado con estado **En Revisión**. Pruébalo
en `Bandeja TIC` (solo Administrador): apruébalo u obsérvalo.

### 6.3 Importar un Excel de prueba

1. Crea un Excel con columnas, por ejemplo: `Código del Bien`, `Bien`, `Custodio Actual`, `Ubicación de Bodega`, `Estado Bien` (o cualquiera de los alias admitidos, ver `/inventario-previo/cargar`).
2. Ve a `Inventario Previo -> Cargar Excel`, sube el archivo.
3. Verás el resumen (filas leídas / nuevas / actualizadas / omitidas).
4. En `Inventario Previo`, valida las filas que quieras migrar (botón "Validar").
5. Pulsa "Pasar al Inventario General": hace upsert por código hacia `inventario` (solo de las filas verificadas).

### 6.4 Exportar a Excel

Desde `/inventario`, botón "Exportar Excel" (exporta todo, o solo lo filtrado si hay un término de búsqueda activo `?q=`).

### 6.5 Descargar acta PDF con QR

Desde la tabla de `/inventario`, ícono de PDF en la fila de un bien → descarga un acta con los datos del bien y un código QR de verificación.

### 6.6 Probar la API con JWT (curl)

```bash
# 1) Login -> obtener token
curl -X POST http://localhost:5000/api/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"username\": \"admin\", \"password\": \"Inamhi2026*\"}"

# Respuesta: {"access_token": "...", "usuario": {...}}

# 2) Usar el token para consultar el usuario actual
curl http://localhost:5000/api/auth/me ^
  -H "Authorization: Bearer TU_TOKEN_AQUI"

# 3) Listar bienes (paginado)
curl "http://localhost:5000/api/bienes?pagina=1&por_pagina=10" ^
  -H "Authorization: Bearer TU_TOKEN_AQUI"
```

(En Linux/Mac reemplaza el `^` de continuación de línea por `\`.)

En Postman: `POST /api/auth/login` con body JSON, copia `access_token` de la
respuesta y colócalo en la pestaña **Authorization -> Bearer Token** de las
siguientes peticiones.

## 7. Respaldos de la base de datos

El módulo `app/utils/backup.py` ejecuta `mysqldump` vía `subprocess` y
conserva solo los últimos 5 respaldos en `respaldos/`. Puedes invocarlo desde
una shell de Python dentro del entorno virtual:

```python
from app import create_app
from app.utils.backup import generar_respaldo

app = create_app()
with app.app_context():
    ruta = generar_respaldo(app.config)
    print(f"Respaldo generado en: {ruta}")
```

(Probado end-to-end contra una instancia real de MySQL 8 durante el desarrollo: genera el `.sql` correctamente vía `mysqldump` y purga los respaldos más antiguos cuando hay más de 5.)

Si `mysqldump` no está en el PATH, configura `MYSQLDUMP_PATH` en `.env` con
la ruta completa al ejecutable (ej. `C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe`).

## 8. Notas de diseño relevantes

- **Roles**: los checks de rol se normalizan (`lowercase` + `strip`); el rol
  técnico matchea por subcadena (`"tecnico"` o `"técnico"`), igual que el
  sistema original.
- **Un bien Aprobado** solo puede editarlo el Administrador.
- **Import de Excel**: nunca escribe directo en `inventario`; siempre pasa
  primero por `inventario_previo` (staging). Si el mismo código de bien
  aparece repetido en el Excel, se conserva la fila más completa (más campos
  llenos), no la primera encontrada.
- **Fechas/números sucios** en datos históricos se guardan como `NULL` en vez
  de fallar la carga completa.
- **Auditoría**: `bitacora_auditoria` no tiene FK hacia `inventario` ni
  `usuarios` a propósito (son snapshots de texto; el sistema audita después
  de eliminar un bien, o referencia usuarios ya eliminados).
- **Dos capas de autenticación, una sola fuente de verdad**: tanto la sesión
  de las páginas HTML como el JWT de `/api/` validan contra el mismo modelo
  `Usuario` y el mismo hash bcrypt.
