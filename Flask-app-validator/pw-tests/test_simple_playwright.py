"""
Simple test to verify Playwright UI validation works.
"""

import asyncio
import sys
from pathlib import Path

# Add the validator directory to the path
sys.path.insert(0, str(Path(__file__).parent / "validator"))

from playwright_runner import PlaywrightUIRunner

async def test_simple_playwright():
    """Test Playwright UI runner with a simple test."""
    print("Testing Simple Playwright UI Runner")
    print("=" * 40)
    
    try:
        # Create a simple test rules file
        test_rules = {
            "ui_tests": [
                {
                    "route": "/",
                    "page_title": "Example Domain",
                    "description": "Test basic page load",
                    "test_cases": [
                        {
                            "name": "Basic Page Load",
                            "description": "Test that a page loads successfully",
                            "actions": [
                                {
                                    "identifier_type": "text",
                                    "identifier_name": "Example Domain",
                                    "check_type": "exists",
                                    "description": "Page title should be present"
                                }
                            ],
                            "expected_result": {
                                "type": "success",
                                "all_elements_present": True
                            },
                            "timeout": 5,
                            "points": 5
                        }
                    ]
                }
            ]
        }
        
        # Save test rules to a temporary file
        import json
        test_rules_file = "test_simple_rules.json"
        with open(test_rules_file, "w") as f:
            json.dump(test_rules, f, indent=2)
        
        print(f"Created test rules file: {test_rules_file}")
        
        # Test with a simple external website
        runner = PlaywrightUIRunner("https://example.com")
        
        print("Initializing Playwright...")
        await runner.initialize()
        
        print("Running UI validation...")
        results = await runner.run_ui_validation(test_rules_file)
        
        print(f"Results: {len(results)} tests completed")
        for result in results:
            status = result.get('status', 'UNKNOWN')
            test_name = result.get('test', 'Unknown')
            duration = result.get('duration', 0.0)
            screenshot = result.get('screenshot', '')
            
            print(f"  {test_name}: {status} ({duration:.2f}s)")
            if screenshot:
                print(f"    Screenshot: {screenshot}")
        
        # Cleanup
        await runner._cleanup()
        
        # Remove test file
        Path(test_rules_file).unlink()
        
        print("[SUCCESS] Playwright UI test completed successfully")
        return True
        
    except Exception as e:
        print(f"[ERROR] Playwright UI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(test_simple_playwright())
        if success:
            print("\n[PASS] Simple Playwright test completed successfully")
        else:
            print("\n[FAIL] Simple Playwright test failed")
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
