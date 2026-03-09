"""
Ollama Model Loader for Studaxis Boot Sequence

Verifies Ollama is available, ensures the target model exists, and optionally
warms it up with a minimal generation so subsequent inference is faster.
Used during the one-time model initialization screen.
"""

from __future__ import annotations

import os
from typing import Tuple

# Model name: prefer env, fallback to shared constant, then default
_OLLAMA_MODEL_ENV = "OLLAMA_MODEL"
_DEFAULT_MODEL = "llama3.2:3b"  # fallback only; model_config picks by RAM (e.g. 7b for 16GB)


def _get_model_name() -> str:
    """Resolve Ollama model name from environment or defaults."""
    return os.environ.get(_OLLAMA_MODEL_ENV, _DEFAULT_MODEL).strip() or _DEFAULT_MODEL


def load_ollama_model() -> Tuple[bool, str | None]:
    """
    Verify Ollama availability, ensure model exists, and warm it up.

    Returns:
        (success, error_message) - error_message is None on success.
    """
    try:
        import ollama
    except ImportError:
        return False, "Ollama Python package not installed. Run: pip install ollama"

    model_name = _get_model_name()

    # 1. List models to verify Ollama daemon is reachable and model exists
    try:
        list_response = ollama.list()
    except Exception as e:
        return False, (
            "Ollama not reachable. Ensure Ollama is running (ollama serve). "
            f"Error: {e}"
        )

    # Check if our model (or alias) is available
    # ListResponse.models: each Model has .model (str)
    models = getattr(list_response, "models", None) or []
    model_names = []
    for m in models:
        name = getattr(m, "model", None) or (m.get("model") if isinstance(m, dict) else None)
        if name:
            model_names.append(name)

    # Accept exact match or base name (e.g. llama3.2:3b, llama3.2:latest, llama3:3b)
    base = model_name.split(":")[0]
    model_found = any(
        nm == model_name or nm.startswith(base + ":") or nm == base
        for nm in model_names
    )

    if not model_found:
        return False, (
            f"Model '{model_name}' not found. Run: ollama pull {model_name}"
        )

    # 2. Warm up: run a minimal generation to load model into memory
    try:
        ollama.generate(
            model=model_name,
            prompt="Hi",
            options={"num_predict": 1},
        )
    except Exception:
        # Model exists but warm-up failed - still proceed; first real request will load it
        pass

    return True, None
