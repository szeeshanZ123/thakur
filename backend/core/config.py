"""
Application configuration and settings loader.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Base project root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Backend network settings
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")

# Storage paths
DATA_DIR = os.getenv("DATA_DIR", "data/")
MODEL_SAVE_DIR = os.getenv("MODEL_SAVE_DIR", "models/")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/treasure_ledger.db")

# CORS and Frontend settings
CORS_ORIGINS_RAW = os.getenv("CORS_ORIGINS", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8080",
]

if CORS_ORIGINS_RAW.strip():
    CORS_ORIGINS = [orig.strip() for orig in CORS_ORIGINS_RAW.split(",") if orig.strip()]
else:
    CORS_ORIGINS = DEFAULT_CORS_ORIGINS

if FRONTEND_URL and FRONTEND_URL not in CORS_ORIGINS:
    CORS_ORIGINS.append(FRONTEND_URL)

# Ensure SQLite parent directory exists if using default local path
if DATABASE_URL.startswith("sqlite:///"):
    sqlite_path = DATABASE_URL.replace("sqlite:///", "")
    if not os.path.isabs(sqlite_path):
        sqlite_file = BASE_DIR / sqlite_path
    else:
        sqlite_file = Path(sqlite_path)
    os.makedirs(sqlite_file.parent, exist_ok=True)

