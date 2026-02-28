"""
Studaxis Initialization Script
Validates environment and sets up initial configuration
"""

import sys
import os
import subprocess
from pathlib import Path


def check_python_version():
    """Verify Python version"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"❌ Python 3.9+ required. Current: {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_ollama():
    """Verify Ollama is installed"""
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Ollama installed")
            
            # Check if llama3:3b is available
            if 'llama3:3b' in result.stdout:
                print("✅ Llama 3.2 3B model available")
            else:
                print("⚠️  Llama 3.2 3B not found. Run: ollama pull llama3:3b")
            return True
        return False
    except FileNotFoundError:
        print("❌ Ollama not found. Install from: https://ollama.com/download")
        return False


def check_dependencies():
    """Check if required packages are installed"""
    required = ['streamlit', 'chromadb', 'ollama', 'boto3', 'psutil']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing.append(package)
            print(f"❌ {package} not installed")
    
    if missing:
        print(f"\n⚠️  Install missing packages: pip install {' '.join(missing)}")
        return False
    return True


def create_env_file():
    """Create .env file from example if it doesn't exist"""
    env_path = Path('.env')
    example_path = Path('.env.example')
    
    if not env_path.exists() and example_path.exists():
        import shutil
        shutil.copy(example_path, env_path)
        print("✅ Created .env file from template")
        print("⚠️  Update .env with your AWS credentials")
    elif env_path.exists():
        print("✅ .env file exists")
    else:
        print("⚠️  .env.example not found")


def create_data_directories():
    """Ensure data directories exist"""
    dirs = [
        'data/chromadb',
        'data/sample_textbooks',
        'data/backups'
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print("✅ Data directories created")


def test_hardware():
    """Run hardware validation"""
    try:
        from local_app.hardware_validator import HardwareValidator
        
        validator = HardwareValidator()
        is_valid, message, specs = validator.validate()
        
        print("\n" + "="*50)
        print("HARDWARE VALIDATION")
        print("="*50)
        print(message)
        print(f"\nRAM: {specs['ram_gb']}GB")
        print(f"CPU: {specs['cpu_count']} cores")
        print(f"Disk: {specs['disk_free_gb']}GB free")
        print(f"Recommended Quantization: {validator.get_quantization_recommendation()}")
        
        return is_valid
    except Exception as e:
        print(f"⚠️  Hardware validation failed: {e}")
        return True  # Don't block initialization


def main():
    """Run all initialization checks"""
    print("="*50)
    print("STUDAXIS INITIALIZATION")
    print("="*50)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Ollama", check_ollama),
        ("Dependencies", check_dependencies),
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"\nChecking {name}...")
        if not check_func():
            all_passed = False
    
    print("\n" + "="*50)
    print("SETUP")
    print("="*50)
    
    create_env_file()
    create_data_directories()
    test_hardware()
    
    print("\n" + "="*50)
    if all_passed:
        print("✅ INITIALIZATION COMPLETE")
        print("="*50)
        print("\nNext steps:")
        print("1. Update .env with your configuration")
        print("2. Run: streamlit run local-app/streamlit_app.py")
    else:
        print("⚠️  INITIALIZATION INCOMPLETE")
        print("="*50)
        print("\nResolve the issues above and run again:")
        print("python init.py")


if __name__ == "__main__":
    main()
