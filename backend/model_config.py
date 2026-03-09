"""
Hardware-aware model selection for Studaxis.

At startup, uses psutil to detect total RAM and selects the appropriate
Ollama model quantization. Only the model for this machine is used—no others.
Models are pulled on first run via `ollama pull <model_name>`.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

# Models by RAM threshold (only one is ever selected per machine)
MODEL_LOW_RAM = "llama3.2:latest"
MODEL_MID_RAM = "llama3.2:latest"
MODEL_HIGH_RAM = "llama3.2:latest"
RAM_THRESHOLD_GB = 6.0   # below this use low-RAM 3b
RAM_HIGH_GB = 14.0       # 14+ GB → use 3b q4_K_M model

# Module-level cache after get_best_model() or load_config()
_selected_model: Optional[str] = None

# Config paths: prefer user appdata, fallback to backend/data
def _config_path() -> Path:
    """Return path to model config file."""
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            p = Path(appdata) / "Studaxis" / "models" / "config.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
    # Unix fallback: ~/.config/Studaxis/models/config.json
    xdg = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    cfg = Path(xdg) / "Studaxis" / "models" / "config.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    return cfg


def _fallback_config_path() -> Path:
    """Fallback path under backend/data for when appdata is unavailable."""
    backend_dir = Path(__file__).resolve().parent
    data_dir = backend_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "model_config.json"


def get_best_model(force_refresh: bool = False) -> str:
    """
    Select the best model for this machine's RAM and persist to config.

    - RAM < 6 GB  → llama3.2:3b-instruct-q2_K (~1.1 GB)
    - 6–14 GB    → llama3.2:3b-instruct-q4_K_M (~1.8 GB)
    - RAM >= 14 GB (e.g. 16 GB) → llama3.2:3b-instruct-q4_K_M (~1.8 GB)

    Env override: STUDAXIS_OLLAMA_MODEL or OLLAMA_MODEL skips hardware selection.
    Returns the selected model name. Called at backend startup.
    """
    global _selected_model

    override = os.environ.get("STUDAXIS_OLLAMA_MODEL") or os.environ.get("OLLAMA_MODEL")
    if override and override.strip():
        _selected_model = override.strip()
        return _selected_model

    if _selected_model is not None and not force_refresh:
        return _selected_model

    ram_gb: float = 4.0  # safe default
    try:
        import psutil
        ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    except Exception:
        pass

    if ram_gb >= RAM_HIGH_GB:
        model = MODEL_HIGH_RAM   # 3b q4 for 14+ GB (e.g. 16 GB)
    elif ram_gb >= RAM_THRESHOLD_GB:
        model = MODEL_MID_RAM    # 3b q4 for 6–14 GB
    else:
        model = MODEL_LOW_RAM
    _selected_model = model

    config = {
        "model": model,
        "ram_gb": round(ram_gb, 2),
        "ram_threshold_gb": RAM_THRESHOLD_GB,
        "ram_high_gb": RAM_HIGH_GB,
    }

    for path_fn in (_config_path, _fallback_config_path):
        try:
            p = path_fn()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(config, indent=2), encoding="utf-8")
            break
        except OSError:
            continue

    return model


def load_config() -> Optional[str]:
    """
    Load stored model from config file. Returns model name or None if not found.
    Used when startup has not yet run (e.g. direct import).
    """
    global _selected_model

    if _selected_model is not None:
        return _selected_model

    for path_fn in (_config_path, _fallback_config_path):
        try:
            p = path_fn()
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                model = data.get("model")
                if model:
                    _selected_model = model
                    return model
        except (OSError, json.JSONDecodeError, KeyError):
            continue
    return None


def get_selected_model() -> str:
    """
    Return the selected model name. Ensures config exists by calling get_best_model if needed.
    Used by ai_integration_layer.py and ai_chat/main.py.
    """
    global _selected_model
    override = os.environ.get("STUDAXIS_OLLAMA_MODEL") or os.environ.get("OLLAMA_MODEL")
    if override and override.strip():
        return override.strip()
    if _selected_model is not None:
        return _selected_model
    loaded = load_config()
    if loaded:
        return loaded
    return get_best_model()


_availability_warned = False


def ensure_model_available(model_name: Optional[str] = None) -> bool:
    """
    Check if the selected model is present in Ollama. If not, print instructions once.

    Returns True if model is available, False otherwise.
    Called before first AI inference.
    """
    global _availability_warned
    model = model_name or get_selected_model()
    base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    url = f"{base}/api/tags"

    try:
        import urllib.request
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        if not _availability_warned:
            print("Ollama not reachable. Start with: ollama serve", file=sys.stderr)
            _availability_warned = True
        return False

    models = data.get("models", [])
    names = [m.get("name", "") for m in models if m.get("name")]

    # Ollama returns names like "llama3.2:3b-instruct-q2_K"; check exact or prefix match
    if model in names:
        return True
    for n in names:
        if n == model or n.startswith(model + ":") or model.startswith(n):
            return True

    if not _availability_warned:
        print(
            f"Downloading model for your hardware... Run: ollama pull {model}",
            file=sys.stderr,
        )
        _availability_warned = True
    return False
