#!/usr/bin/env python3
"""
Test script to verify Playwright fix on Windows.
This script tests the Playwright UI runner directly without subprocess issues.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the validator directory to the path
sys.path.insert(0, str(Path(__file__).parent / "validator"))

def test_playwright_initialization():
    """Test Playwright initialization with Windows fixes."""
    try:
        from playwright_runner import PlaywrightUIRunner
        
        print("Testing Playwright initialization...")
        
        # Set Windows event loop policy
        import platform
        if platform.system() == "Windows":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                print("[OK] Set Windows event loop policy")
            except Exception as e:
                print(f"[WARN] Could not set Windows event loop policy: {e}")
        
        # Test initialization
        async def test_init():
            runner = PlaywrightUIRunner("http://127.0.0.1:5000")
            try:
                await runner.initialize()
                print("[OK] Playwright initialized successfully")
                await runner._cleanup()
                print("[OK] Playwright cleanup completed")
                return True
            except Exception as e:
                print(f"[FAIL] Playwright initialization failed: {e}")
                return False
        
        # Run the test
        result = asyncio.run(test_init())
        return result
        
    except ImportError as e:
        print(f"[FAIL] Import error: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        return False

def test_playwright_with_rules():
    """Test Playwright with actual rules file."""
    try:
        from playwright_runner import PlaywrightUIRunner
        
        # Check if rules file exists
        rules_file = Path("streamlit_app/rules/defaultRules.json")
        if not rules_file.exists():
            print(f"[FAIL] Rules file not found: {rules_file}")
            return False
        
        print("Testing Playwright with rules file...")
        
        # Set Windows event loop policy
        import platform
        if platform.system() == "Windows":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception as e:
                print(f"[WARN] Could not set Windows event loop policy: {e}")
        
        # Test with rules
        async def test_with_rules():
            runner = PlaywrightUIRunner("http://127.0.0.1:5000")
            try:
                # Just test initialization, don't run actual tests
                await runner.initialize()
                print("[OK] Playwright initialized with rules file")
                
                # Test loading rules
                rules_data = runner._load_rules(str(rules_file))
                ui_tests = rules_data.get("ui_tests", [])
                print(f"[OK] Loaded {len(ui_tests)} UI test routes from rules file")
                
                await runner._cleanup()
                print("[OK] Playwright cleanup completed")
                return True
            except Exception as e:
                print(f"[FAIL] Playwright test with rules failed: {e}")
                return False
        
        # Run the test
        result = asyncio.run(test_with_rules())
        return result
        
    except ImportError as e:
        print(f"[FAIL] Import error: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Playwright Windows Fix Test")
    print("=" * 60)
    
    # Test 1: Basic initialization
    print("\n1. Testing basic Playwright initialization...")
    test1_result = test_playwright_initialization()
    
    # Test 2: With rules file
    print("\n2. Testing Playwright with rules file...")
    test2_result = test_playwright_with_rules()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"Basic initialization: {'PASS' if test1_result else 'FAIL'}")
    print(f"With rules file: {'PASS' if test2_result else 'FAIL'}")
    
    if test1_result and test2_result:
        print("\n[SUCCESS] All tests passed! Playwright should work now.")
        return 0
    else:
        print("\n[FAILURE] Some tests failed. Check the error messages above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
