"""
Test script to check Playwright setup and installation.
"""

import asyncio
import sys
from pathlib import Path

def test_playwright_installation():
    """Test if Playwright is properly installed."""
    print("Testing Playwright Installation")
    print("=" * 40)
    
    try:
        from playwright.async_api import async_playwright
        print("[OK] Playwright package imported successfully")
    except ImportError as e:
        print(f"[ERROR] Playwright package not found: {e}")
        print("Please install with: pip install playwright")
        return False
    
    try:
        import subprocess
        result = subprocess.run([sys.executable, "-m", "playwright", "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"[OK] Playwright CLI available: {result.stdout.strip()}")
        else:
            print(f"[ERROR] Playwright CLI error: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] Error checking Playwright CLI: {e}")
        return False
    
    return True

async def test_playwright_browser_launch():
    """Test if Playwright can launch a browser."""
    print("\nTesting Playwright Browser Launch")
    print("=" * 40)
    
    try:
        from playwright.async_api import async_playwright
        
        playwright = None
        browser = None
        
        try:
            print("Starting Playwright...")
            playwright = await async_playwright().start()
            print("[OK] Playwright started successfully")
            
            print("Launching browser...")
            browser = await playwright.chromium.launch(headless=True)
            print("[OK] Browser launched successfully")
            
            print("Creating context...")
            context = await browser.new_context()
            print("[OK] Browser context created successfully")
            
            print("Creating page...")
            page = await context.new_page()
            print("[OK] Browser page created successfully")
            
            print("Testing navigation...")
            await page.goto("https://example.com")
            title = await page.title()
            print(f"[OK] Navigation successful - Page title: {title}")
            
            await page.close()
            await context.close()
            await browser.close()
            await playwright.stop()
            
            print("[OK] All Playwright operations completed successfully")
            return True
            
        except Exception as e:
            print(f"[ERROR] Playwright operation failed: {e}")
            if browser:
                try:
                    await browser.close()
                except:
                    pass
            if playwright:
                try:
                    await playwright.stop()
                except:
                    pass
            return False
            
    except Exception as e:
        print(f"[ERROR] Playwright test failed: {e}")
        return False

def test_playwright_browsers_installed():
    """Check if Playwright browsers are installed."""
    print("\nTesting Playwright Browsers Installation")
    print("=" * 40)
    
    try:
        import subprocess
        result = subprocess.run([sys.executable, "-m", "playwright", "install", "--dry-run"], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("[OK] Playwright browsers check completed")
            if "chromium" in result.stdout.lower():
                print("[OK] Chromium browser detected")
            else:
                print("[WARN] Chromium browser not found - may need installation")
        else:
            print(f"[ERROR] Playwright browsers check failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] Error checking Playwright browsers: {e}")
        return False
    
    return True

async def main():
    """Run all Playwright tests."""
    print("Playwright Setup Test")
    print("=" * 50)
    
    # Test 1: Package installation
    if not test_playwright_installation():
        print("\n[ERROR] Playwright installation test failed")
        return False
    
    # Test 2: Browser installation
    if not test_playwright_browsers_installed():
        print("\n[ERROR] Playwright browsers test failed")
        print("Try running: python -m playwright install")
        return False
    
    # Test 3: Browser launch
    if not await test_playwright_browser_launch():
        print("\n[ERROR] Playwright browser launch test failed")
        return False
    
    print("\n[SUCCESS] All Playwright tests passed!")
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        if success:
            print("\n[PASS] Playwright setup is working correctly")
        else:
            print("\n[FAIL] Playwright setup has issues")
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
