"""
Test script to verify Playwright backend fixes.
"""

import asyncio
import sys
from pathlib import Path

# Add the playwright_backend directory to the path
sys.path.insert(0, str(Path(__file__).parent / "playwright_backend"))

from runner import PlaywrightTestRunner

async def test_playwright_backend():
    """Test the Playwright backend with a simple test."""
    print("Testing Playwright backend...")
    
    runner = PlaywrightTestRunner()
    
    try:
        # Initialize Playwright
        await runner.initialize()
        print("[OK] Playwright initialized")
        
        # Run tests with a simple URL
        results = await runner.run_tests(
            base_url="http://httpbin.org/get",
            test_suite="default", 
            project_name="test_project",
            timeout=10,
            headless=True,
            capture_screenshots=False
        )
        
        print(f"[OK] Tests completed: {len(results)} results")
        
        for result in results:
            status = result.get("status", "UNKNOWN")
            name = result.get("name", "Unknown")
            duration = result.get("duration", 0.0)
            error = result.get("error", "")
            
            print(f"  - {name}: {status} ({duration:.2f}s)")
            if error:
                print(f"    Error: {error}")
        
        return len(results) > 0
        
    except Exception as e:
        print(f"[ERROR] Error testing Playwright backend: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await runner._cleanup()
        print("[OK] Cleanup completed")

if __name__ == "__main__":
    success = asyncio.run(test_playwright_backend())
    if success:
        print("\n[PASS] Playwright backend test PASSED")
    else:
        print("\n[FAIL] Playwright backend test FAILED")
