"""Configuración de la aplicación"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Rutas
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Base de datos MySQL (para conexión en red)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "siigo_python")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# Carpetas de monitoreo
WATCH_FOLDER = os.getenv("WATCH_FOLDER", r"D:\SIIWI01\DOCELECTRONICOS")
PROCESSED_FOLDER = os.getenv("PROCESSED_FOLDER", r"D:\SIIWI01\DOCELECTRONICOS\procesados")

# API DIAN
APIDIAN_URL = os.getenv("APIDIAN_URL", "https://apidian.clipers.pro/api/ubl2.1")

# Tema oscuro (colores similares a Filament)
THEME = {
    "bg_primary": "#0f172a",
    "bg_secondary": "#1e293b",
    "bg_card": "#1e293b",
    "bg_hover": "#334155",
    "text_primary": "#f8fafc",
    "text_secondary": "#94a3b8",
    "border": "#334155",
    "primary": "#3b82f6",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "info": "#06b6d4",
}
