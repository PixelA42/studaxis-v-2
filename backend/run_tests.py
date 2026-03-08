#!/usr/bin/env python3
"""
Quick Test Runner for SyncOrchestrator
═══════════════════════════════════════

Runs all tests and shows summary.
Usage: python run_tests.py
"""

import sys
import subprocess
from pathlib import Path

def run_unit_tests():
    """Run unit tests."""
    print("=" * 60)
    print("RUNNING UNIT TESTS")
    print("=" * 60)
    
    result = subprocess.run(
        [sys.executable, "tests/test_sync_orchestrator.py"],
        cwd=Path(__file__).parent,
        capture_output=False
    )
    
    return result.returncode == 0

def quick_integration_test():
    """Quick integration test."""
    print("\n" + "=" * 60)
    print("QUICK INTEGRATION TEST")
    print("=" * 60)
    
    try:
        from sync_orchestrator import SyncOrchestrator
        
        orch = SyncOrchestrator(base_path=".")
        
        # Test 1: Initial state
        assert orch.get_state() == "IDLE", "Initial state should be IDLE"
        print("✅ Test 1: Initial state correct")
        
        # Test 2: State persistence
        orch.state = "QUEUED"
        orch._save_state()
        orch2 = SyncOrchestrator(base_path=".")
        assert orch2.get_state() == "QUEUED", "State should persist"
        print("✅ Test 2: State persistence works")
        
        # Test 3: Cleanup
        orch.cleanup()
        orch2.cleanup()
        print("✅ Test 3: Cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("\n🧪 SyncOrchestrator Test Suite")
    print("=" * 60)
    
    results = {
        "Unit Tests": run_unit_tests(),
        "Integration": quick_integration_test()
    }
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name:20s} {status}")
    
    print("=" * 60)
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check output above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
