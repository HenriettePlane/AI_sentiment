import os
from dotenv import load_dotenv

load_dotenv()


def _get(key: str, default: str | None = None) -> str | None:
    """Get config from Streamlit secrets (cloud) or env vars (local/CI)."""
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


# BigQuery
GCP_PROJECT = _get("GCP_PROJECT")

# Supabase
SUPABASE_URL = _get("SUPABASE_URL")
SUPABASE_ANON_KEY = _get("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = _get("SUPABASE_SERVICE_ROLE_KEY")

# Retention
RETENTION_DAYS = int(_get("RETENTION_DAYS", "365"))
