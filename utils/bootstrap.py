"""One-time startup bootstrap for a fresh deploy where local disk state doesn't
survive a redeploy (e.g. Streamlit Community Cloud): regenerates gitignored asset
folders (character avatars, weather icons - see README's copyright note on why
they aren't committed) and materializes the login-accounts file from a Streamlit
secret if it isn't already on disk. Called from utils/auth.py::require_login() so
it runs on every page; each check is guarded by st.cache_resource so the actual
work only ever happens once per running server process, not on every rerun.
"""
import subprocess
import sys
from pathlib import Path

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

CHARACTERS_ASSET_DIR = Path("assets/characters")
WEATHER_ASSET_DIR = Path("assets/weather")
AUTH_CONFIG_PATH = Path(".streamlit/auth_config.yaml")


def _has_files(directory: Path) -> bool:
    return directory.is_dir() and any(directory.iterdir())


@st.cache_resource(show_spinner="首次启动，正在下载角色头像与天气图标（仅需一次）…")
def ensure_assets() -> None:
    """Re-fetch assets/characters/*.png and assets/weather/*.png if missing -
    normal on a fresh deploy, since they're gitignored (copyrighted game art, not
    ours to redistribute) and there's no pre-start setup hook on most free hosts."""
    if not _has_files(CHARACTERS_ASSET_DIR):
        subprocess.run([sys.executable, "scripts/scrape_characters.py"], check=True)
    if not _has_files(WEATHER_ASSET_DIR):
        subprocess.run([sys.executable, "scripts/download_weather_icons.py"], check=True)


@st.cache_resource
def ensure_auth_config() -> None:
    """Write .streamlit/auth_config.yaml from a Streamlit secret if it doesn't
    already exist on disk. Lets login accounts survive a redeploy: paste the
    file's content into Community Cloud's Secrets editor as
    `auth_config_yaml = \"\"\"...\"\"\"` once, and every fresh deploy recreates the
    file from that. Local dev (no secrets.toml at all) is unaffected - falls
    through silently so utils/auth.py's own "missing config" message applies."""
    if AUTH_CONFIG_PATH.exists():
        return
    try:
        secret_yaml = st.secrets.get("auth_config_yaml")
    except StreamlitSecretNotFoundError:
        return
    if not secret_yaml:
        return
    AUTH_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUTH_CONFIG_PATH.write_text(secret_yaml, encoding="utf-8")


def ensure_deployment_bootstrap() -> None:
    ensure_assets()
    ensure_auth_config()
