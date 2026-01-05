# FacturaPro - Facturación Electrónica

Aplicación de escritorio para gestionar facturación electrónica con la DIAN Colombia.

## Características

- 📄 Escaneo automático de XMLs
- 📤 Envío de facturas a la DIAN via ApiDian
- 📝 Creación de Notas Crédito y Notas Débito
- 📧 Envío de documentos por correo electrónico
- 📊 Gestión de resoluciones de facturación
- 🔐 Carga de certificado digital
- 🌐 Base de datos MySQL para conexión en red (múltiples puntos)
- 🎨 Interfaz moderna con tema claro/oscuro

## Requisitos

- Python 3.10+
- MySQL Server
- Windows 10/11

## Instalación

1. Crear base de datos MySQL:
```sql
CREATE DATABASE siigo_python CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Copiar `.env.example` a `.env` y configurar:
```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=siigo_python
DB_USER=root
DB_PASSWORD=

WATCH_FOLDER=D:\SIIWI01\DOCELECTRONICOS
PROCESSED_FOLDER=D:\SIIWI01\DOCELECTRONICOS\procesados
```

4. Ejecutar:
```bash
python main.py
```

## Conexión en Red

Para usar desde múltiples puntos de venta:

1. Configurar MySQL para aceptar conexiones remotas
2. En cada punto, configurar `.env` con la IP del servidor:
```env
DB_HOST=192.168.1.100
DB_PORT=3306
DB_NAME=siigo_python
DB_USER=root
DB_PASSWORD=
```

## Compilar a .exe

```bash
build.bat
```

El ejecutable se generará en `dist/FacturaPro.exe`

## Estructura

```
├── main.py              # Punto de entrada
├── config.py            # Configuración (MySQL)
├── database.py          # Modelos SQLAlchemy
├── .env                 # Variables de entorno
├── services/
│   ├── xml_parser.py    # Parser de XMLs
│   ├── api_dian.py      # Cliente ApiDian
│   └── folder_watcher.py
└── views/
    ├── documents.py     # Vista de documentos
    ├── resolutions.py   # Vista de resoluciones
    ├── settings.py      # Vista de configuración
    └── theme.py         # Tema claro/oscuro
```

## Uso

1. **Configuración**: Ir a "Configuración" y llenar datos de empresa, API, certificado y correo
2. **Certificado**: Subir certificado digital (.p12 o .pfx) en la pestaña "Certificado"
3. **Resoluciones**: Crear las resoluciones de facturación (Factura, NC, ND)
4. **Documentos**: Escanear carpeta de XMLs y enviar a la DIAN
