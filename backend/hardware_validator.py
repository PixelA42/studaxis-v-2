"""
Hardware Validation Module
Checks system resources (RAM, CPU, disk) on app launch.
Also ensures Ollama is running and the required model is pulled at startup.
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

import psutil
import platform
from typing import Dict, Tuple


def _ollama_base_url() -> str:
    return os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


def _ollama_ping(timeout: float = 2.0) -> bool:
    """Return True if Ollama API is reachable."""
    base = _ollama_base_url()
    url = f"{base}/api/tags"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as _:
            return True
    except Exception:
        return False


def ensure_ollama_serve(max_wait_seconds: float = 15.0) -> bool:
    """
    Ensure Ollama server is running. If not reachable, start `ollama serve`
    in the background and wait until the API responds (or max_wait_seconds).
    Returns True if Ollama is reachable at the end, False otherwise.
    """
    if _ollama_ping():
        return True
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                ["ollama", "serve"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
            )
        else:
            subprocess.Popen(
                ["ollama", "serve"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
    except FileNotFoundError:
        return False
    deadline = time.monotonic() + max_wait_seconds
    while time.monotonic() < deadline:
        time.sleep(2.0)
        if _ollama_ping():
            return True
    return False


def _model_in_list(model_name: str, names: list) -> bool:
    """Check if model_name is present in Ollama model names (exact or alias)."""
    if model_name in names:
        return True
    for n in names:
        if n == model_name or n.startswith(model_name + ":") or model_name.startswith(n):
            return True
    return False


def ensure_ollama_model(model_name: str, timeout_pull_seconds: int = 3600) -> bool:
    """
    Ensure the required Ollama model is pulled. If not present, run
    `ollama pull <model_name>` and wait for completion.
    Returns True if the model is available (already present or pulled), False otherwise.
    """
    base = _ollama_base_url()
    url = f"{base}/api/tags"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return False
    models = data.get("models", [])
    names = [m.get("name", "") for m in models if m.get("name")]
    if _model_in_list(model_name, names):
        return True
    try:
        result = subprocess.run(
            ["ollama", "pull", model_name],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_pull_seconds,
        )
        if result.returncode != 0:
            return False
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


class HardwareValidator:
    """Validates hardware meets minimum requirements for Studaxis"""
    
    # Minimum requirements
    MIN_RAM_GB = 4.0
    MIN_DISK_GB = 2.0
    RECOMMENDED_RAM_GB = 6.0
    
    def __init__(self):
        self.specs = self._gather_specs()
    
    def _gather_specs(self) -> Dict:
        """Gather system specifications"""
        ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        disk_gb = psutil.disk_usage('/').free / (1024 ** 3)
        
        return {
            'ram_gb': round(ram_gb, 2),
            'ram_available_gb': round(psutil.virtual_memory().available / (1024 ** 3), 2),
            'cpu_count': psutil.cpu_count(logical=False),
            'cpu_count_logical': psutil.cpu_count(logical=True),
            'cpu_model': platform.processor() or 'Unknown',
            'disk_free_gb': round(disk_gb, 2),
            'os': platform.system(),
            'os_version': platform.version()
        }
    
    def validate(self) -> Tuple[bool, str, Dict]:
        """
        Validate hardware against requirements
        
        Returns:
            Tuple of (is_valid, message, specs)
        """
        specs = self.specs
        warnings = []
        critical = []
        
        # RAM check
        if specs['ram_gb'] < self.MIN_RAM_GB:
            critical.append(f"⚠️ RAM: {specs['ram_gb']}GB (minimum {self.MIN_RAM_GB}GB required)")
        elif specs['ram_gb'] < self.RECOMMENDED_RAM_GB:
            warnings.append(f"⚠️ RAM: {specs['ram_gb']}GB (recommended {self.RECOMMENDED_RAM_GB}GB)")
        
        # Disk check
        if specs['disk_free_gb'] < self.MIN_DISK_GB:
            critical.append(f"⚠️ Disk: {specs['disk_free_gb']}GB free (minimum {self.MIN_DISK_GB}GB required)")
        
        # CPU check (informational)
        if specs['cpu_count'] < 2:
            warnings.append(f"ℹ️ CPU: {specs['cpu_count']} cores (2+ recommended for better performance)")
        
        # Build message
        if critical:
            message = "❌ Critical Issues:\n" + "\n".join(critical)
            message += "\n\nStudaxis may not run properly. Consider upgrading hardware."
            return False, message, specs
        
        if warnings:
            message = "✅ System meets minimum requirements\n\n⚠️ Recommendations:\n" + "\n".join(warnings)
            return True, message, specs
        
        message = "✅ System meets all recommended requirements"
        return True, message, specs
    
    def get_optimization_tips(self) -> list:
        """Get optimization tips based on hardware"""
        tips = []
        specs = self.specs
        
        if specs['ram_gb'] < self.RECOMMENDED_RAM_GB:
            tips.append("💡 Close other applications to free up RAM")
            tips.append("💡 System will use Q2_K quantization (optimized for 4GB RAM)")
        
        if specs['disk_free_gb'] < 5:
            tips.append("💡 Free up disk space by removing unused files")
            tips.append("💡 Limit number of embedded textbooks to save space")
        
        if specs['cpu_count'] < 2:
            tips.append("💡 Inference may take 10-15 seconds on single-core CPUs")
            tips.append("💡 Consider using shorter context windows")
        
        return tips
    
    def get_quantization_recommendation(self) -> str:
        """Recommend quantization level based on RAM"""
        ram = self.specs['ram_gb']
        
        if ram >= 8:
            return "Q4_K_M"  # Best quality
        elif ram >= 6:
            return "Q3_K_S"  # Balanced
        else:
            return "Q2_K"    # Optimized for 4GB
    
    def monitor_runtime_memory(self) -> Dict:
        """Monitor memory usage during runtime"""
        mem = psutil.virtual_memory()
        return {
            'used_gb': round(mem.used / (1024 ** 3), 2),
            'available_gb': round(mem.available / (1024 ** 3), 2),
            'percent': mem.percent
        }


# Standalone test
if __name__ == "__main__":
    validator = HardwareValidator()
    validator.validate()
