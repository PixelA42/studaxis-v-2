"""
Studaxis — Device ID Generator
═══════════════════════════════
Generate and persist unique device identifier.

This module ensures each device has a stable, unique identifier that persists
across app restarts. Used for sync conflict resolution and device tracking.
"""

import uuid
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from path_config import get_data_dir

DEVICE_ID_FILE = get_data_dir() / "device_id.json"


def get_or_generate_device_id() -> str:
    """
    Return persistent device ID (UUID).
    Generated once on first launch, stored in device_id.json.
    
    Returns:
        str: UUID v4 device identifier
    """
    if DEVICE_ID_FILE.exists():
        try:
            data = json.loads(DEVICE_ID_FILE.read_text(encoding="utf-8"))
            device_id = data.get("device_id")
            if device_id and isinstance(device_id, str):
                return device_id
        except (OSError, json.JSONDecodeError):
            pass
    
    # Generate new device ID
    device_id = str(uuid.uuid4())
    
    # Persist with metadata
    DEVICE_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    device_data = {
        "device_id": device_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platform": _get_platform_info(),
    }
    
    tmp = DEVICE_ID_FILE.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(device_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    tmp.replace(DEVICE_ID_FILE)
    
    return device_id


def get_device_id() -> Optional[str]:
    """
    Return device ID if exists, None otherwise.
    
    Use this when device ID is optional.
    Use get_or_generate_device_id() when device ID is required.
    """
    if DEVICE_ID_FILE.exists():
        try:
            data = json.loads(DEVICE_ID_FILE.read_text(encoding="utf-8"))
            return data.get("device_id")
        except (OSError, json.JSONDecodeError):
            return None
    return None


def _get_platform_info() -> str:
    """Get basic platform identifier for debugging (not for security)."""
    try:
        import platform
        return f"{platform.system()} {platform.release()}"
    except Exception:
        return "unknown"


# ── Standalone test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing device ID generation...")
    
    # First call generates
    device_id_1 = get_or_generate_device_id()
    print(f"Generated device ID: {device_id_1}")
    
    # Second call returns same ID
    device_id_2 = get_or_generate_device_id()
    print(f"Retrieved device ID: {device_id_2}")
    
    assert device_id_1 == device_id_2, "Device ID should be stable"
    print("✅ Device ID is persistent")
    
    # Check file structure
    if DEVICE_ID_FILE.exists():
        data = json.loads(DEVICE_ID_FILE.read_text())
        print(f"Device data: {json.dumps(data, indent=2)}")
    
    print("✅ All tests passed")
