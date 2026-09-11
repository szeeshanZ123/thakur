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

# Ensure SQLite parent directory exists if using default local path
if DATABASE_URL.startswith("sqlite:///"):
    sqlite_path = DATABASE_URL.replace("sqlite:///", "")
    if not os.path.isabs(sqlite_path):
        sqlite_file = BASE_DIR / sqlite_path
    else:
        sqlite_file = Path(sqlite_path)
    os.makedirs(sqlite_file.parent, exist_ok=True)
