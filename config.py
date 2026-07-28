import os
import sys
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Find the absolute path to the project root directory
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Load environment variables from .env file
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Add PROJECT_ROOT to sys.path so we can import config from subdirectories
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

def _get_setting(key, default=None):
    """Retrieve setting from os.environ, falling back to st.secrets if available."""
    val = os.getenv(key)
    if val is not None and val != "":
        return val
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return default

# MySQL Database credentials
DB_USER = _get_setting("DB_USER")
DB_PASSWORD = _get_setting("DB_PASSWORD")
DB_HOST = _get_setting("DB_HOST", "127.0.0.1")
DB_PORT = _get_setting("DB_PORT", "3306")
DB_NAME = _get_setting("DB_NAME", "skillscavenge")
DB_USE_SSL = str(_get_setting("DB_USE_SSL", "false")).lower() == "true"

# Adzuna API credentials
ADZUNA_APP_ID = _get_setting("ADZUNA_APP_ID")
ADZUNA_APP_KEY = _get_setting("ADZUNA_APP_KEY")

def get_db_url():
    """Returns the SQLAlchemy database URL."""
    password = DB_PASSWORD if DB_PASSWORD else ""
    return f"mysql+pymysql://{DB_USER}:{quote_plus(password)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_sqlalchemy_engine():
    """Returns a SQLAlchemy engine using the shared configuration."""
    from sqlalchemy import create_engine
    connect_args = {}
    if DB_USE_SSL:
        # Aiven requires ssl-mode=REQUIRED, which in pymysql can be achieved by passing an empty ssl dict 
        # or specifying ssl_mode. For general PyMySQL with SQLAlchemy, this enforces SSL.
        connect_args = {"ssl": {"ssl_mode": "REQUIRED"}}
        
    return create_engine(get_db_url(), pool_pre_ping=True, connect_args=connect_args)

