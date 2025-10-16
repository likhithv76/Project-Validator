"""
Playwright runner for dynamic UI validation based on JSON rules.
Handles route-based testing, form interaction, and result collection.
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, expect

try:
    from .test_data_generator import test_data_generator
except ImportError:
    try:
        from validator.test_data_generator import test_data_generator
    except ImportError:
        # Fallback for when running as standalone
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent))
        from test_data_generator import test_data_generator

class PlaywrightUIRunner:
    """
    Handles Playwright UI validation based on JSON rules.
    Dynamically tests routes, forms, and user interactions.
    """
    
    def __init__(self, base_url: str = "http://127.0.0.1:5000"):
        self.base_url = base_url.rstrip('/')
        self.playwright = None
        self.browser = None
        self.context = None
        self.results = []
        self.logs = []
        self.screenshots_dir = Path("Logs") / "screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
    async def initialize(self):
        """Initialize Playwright and browser."""
        try:
            # Set up Windows-specific event loop policy if needed
            import platform
            if platform.system() == "Windows":
                try:
                    import asyncio
                    # Try to set the Windows-specific event loop policy
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                except Exception as e:
                    self.log(f"Could not set Windows event loop policy: {e}", level="WARN")
            
            # Try to start Playwright with error handling
            self.playwright = await async_playwright().start()
            
            # Try different browser launch strategies
            browser_launch_strategies = [
                # Strategy 1: Standard headless with Windows-specific args
                {
                    "headless": True,
                    "args": [
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-renderer-backgrounding",
                        "--disable-ipc-flooding-protection"
                    ]
                },
                # Strategy 2: Minimal args
                {
                    "headless": True,
                    "args": ["--no-sandbox", "--disable-dev-shm-usage"]
                },
                # Strategy 3: No args
                {
                    "headless": True
                },
                # Strategy 4: Non-headless (fallback)
                {
                    "headless": False,
                    "args": ["--no-sandbox"]
                }
            ]
            
            browser_launched = False
            for i, strategy in enumerate(browser_launch_strategies):
                try:
                    self.log(f"Trying browser launch strategy {i+1}...")
                    self.browser = await self.playwright.chromium.launch(**strategy)
                    browser_launched = True
                    self.log(f"Browser launched successfully with strategy {i+1}")
                    break
                except Exception as e:
                    self.log(f"Strategy {i+1} failed: {e}", level="WARN")
                    if i < len(browser_launch_strategies) - 1:
                        continue
                    else:
                        raise e
            
            if not browser_launched:
                raise Exception("All browser launch strategies failed")
            
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            
            self.log("Playwright UI runner initialized successfully")
            
        except NotImplementedError as e:
            self.log(f"Playwright not supported on this platform: {e}", level="ERROR")
            raise Exception("Playwright is not supported on this Windows configuration. Please install Playwright browsers or use a different environment.")
        except Exception as e:
            self.log(f"Failed to initialize Playwright: {e}", level="ERROR")
            raise
    
    async def run_ui_validation(self, rules_file: str) -> List[Dict[str, Any]]:
        """
        Run UI validation based on rules file.
        
        Args:
            rules_file: Path to JSON rules file containing ui_tests
            
        Returns:
            List of test results
        """
        try:
            await self.initialize()
            
            # Load rules
            rules_data = self._load_rules(rules_file)
            ui_tests = rules_data.get("ui_tests", [])
            
            if not ui_tests:
                self.log("No UI tests found in rules file", level="WARN")
                return []
            
            self.log(f"Found {len(ui_tests)} UI test routes")
            
            # Run tests for each route
            for route_test in ui_tests:
                await self._test_route(route_test)
            
            return self.results
            
        except Exception as e:
            self.log(f"Error during UI validation: {e}", level="ERROR")
            return []
        
        finally:
            await self._cleanup()
    
    def _load_rules(self, rules_file: str) -> Dict[str, Any]:
        """Load rules from JSON file."""
        try:
            with open(rules_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.log(f"Failed to load rules file {rules_file}: {e}", level="ERROR")
            return {}
    
    async def _test_route(self, route_test: Dict[str, Any]):
        """Test a specific route with its test cases."""
        route = route_test.get("route", "")
        page_title = route_test.get("page_title", "")
        test_cases = route_test.get("test_cases", [])
        
        self.log(f"Testing route: {route}")
        
        try:
            # Create new page for this route
            page = await self.context.new_page()
            
            # Navigate to route
            url = f"{self.base_url}{route}"
            await page.goto(url, timeout=10000)
            
            # Verify page title if specified
            if page_title:
                try:
                    await expect(page).to_have_title(page_title)
                    self.log(f"Page title verified: {page_title}")
                except Exception as e:
                    self.log(f"Page title mismatch: {e}", level="WARN")
            
            # Run test cases
            for test_case in test_cases:
                await self._run_test_case(page, route, test_case)
            
            await page.close()
            
        except Exception as e:
            self.log(f"Error testing route {route}: {e}", level="ERROR")
            self.results.append({
                "route": route,
                "test": "Route Navigation",
                "status": "FAIL",
                "duration": 0.0,
                "error": str(e),
                "screenshot": None
            })
    
    async def _run_test_case(self, page: Page, route: str, test_case: Dict[str, Any]):
        """Run a single test case."""
        test_name = test_case.get("name", "Unknown Test")
        identifiers = test_case.get("identifiers", [])
        actions = test_case.get("actions", [])
        expected_result = test_case.get("expected_result", {})
        timeout = test_case.get("timeout", 10)
        points = test_case.get("points", 5)
        
        start_time = time.time()
        
        try:
            self.log(f"Running test case: {test_name}")
            
            # Handle form-based tests (identifiers)
            if identifiers:
                await self._handle_form_test(page, identifiers, expected_result, timeout)
            
            # Handle action-based tests (actions)
            if actions:
                await self._handle_action_test(page, actions, expected_result, timeout)
            
            duration = time.time() - start_time
            
            # Capture screenshot
            screenshot_path = await self._capture_screenshot(page, route, test_name)
            
            self.results.append({
                "route": route,
                "test": test_name,
                "status": "PASS",
                "duration": duration,
                "error": None,
                "screenshot": screenshot_path,
                "points": points
            })
            
            self.log(f"Test case '{test_name}' PASSED in {duration:.2f}s")
            
        except Exception as e:
            duration = time.time() - start_time
            screenshot_path = await self._capture_screenshot(page, route, test_name)
            
            self.results.append({
                "route": route,
                "test": test_name,
                "status": "FAIL",
                "duration": duration,
                "error": str(e),
                "screenshot": screenshot_path,
                "points": 0
            })
            
            self.log(f"Test case '{test_name}' FAILED: {e}", level="ERROR")
    
    async def _handle_form_test(self, page: Page, identifiers: List[Dict], expected_result: Dict, timeout: int):
        """Handle form-based test with input fields and buttons."""
        for identifier in identifiers:
            identifier_type = identifier.get("identifier_type", "class")
            identifier_name = identifier.get("identifier_name", "")
            field_type = identifier.get("type", "text")
            input_value = identifier.get("input_value", "")
            action = identifier.get("action", "fill")
            required = identifier.get("required", False)
            
            # Build selector
            selector = self._build_selector(identifier_type, identifier_name)
            
            try:
                # Wait for element to be visible
                await page.wait_for_selector(selector, timeout=5000)
                
                if field_type in ["short_text", "email", "password"]:
                    # Fill input field
                    if input_value:
                        await page.fill(selector, input_value)
                        self.log(f"Filled {field_type} field '{identifier_name}' with: {input_value}")
                    elif required:
                        raise Exception(f"Required field '{identifier_name}' missing input value")
                
                elif field_type == "button":
                    # Click button
                    if action == "click":
                        await page.click(selector)
                        self.log(f"Clicked button '{identifier_name}'")
                    else:
                        # Just verify button exists
                        await expect(page.locator(selector)).to_be_visible()
                        self.log(f"Verified button '{identifier_name}' exists")
                
                # Small delay between actions
                await page.wait_for_timeout(100)
                
            except Exception as e:
                if required:
                    raise Exception(f"Required element '{identifier_name}' not found or not interactable: {e}")
                else:
                    self.log(f"Optional element '{identifier_name}' not found: {e}", level="WARN")
        
        # Wait for expected result
        await self._wait_for_expected_result(page, expected_result, timeout)
    
    async def _handle_action_test(self, page: Page, actions: List[Dict], expected_result: Dict, timeout: int):
        """Handle action-based test with element checks and clicks."""
        for action in actions:
            identifier_type = action.get("identifier_type", "class")
            identifier_name = action.get("identifier_name", "")
            check_type = action.get("check_type", "exists")
            description = action.get("description", "")
            
            # Build selector
            selector = self._build_selector(identifier_type, identifier_name)
            
            try:
                if check_type == "exists":
                    await expect(page.locator(selector)).to_be_visible()
                    self.log(f"Verified element exists: {description}")
                
                elif check_type == "click":
                    await page.click(selector)
                    self.log(f"Clicked element: {description}")
                
                elif check_type == "text_contains":
                    text_content = await page.locator(selector).text_content()
                    if identifier_name not in text_content:
                        raise Exception(f"Text '{identifier_name}' not found in element")
                    self.log(f"Verified text content: {description}")
                
                # Small delay between actions
                await page.wait_for_timeout(100)
                
            except Exception as e:
                raise Exception(f"Action failed - {description}: {e}")
        
        # Wait for expected result
        await self._wait_for_expected_result(page, expected_result, timeout)
    
    def _build_selector(self, identifier_type: str, identifier_name: str) -> str:
        """Build CSS selector based on identifier type and name."""
        if identifier_type == "class":
            return f".{identifier_name}"
        elif identifier_type == "id":
            return f"#{identifier_name}"
        elif identifier_type == "text":
            return f"text={identifier_name}"
        elif identifier_type == "name":
            return f"[name='{identifier_name}']"
        else:
            return identifier_name
    
    async def _wait_for_expected_result(self, page: Page, expected_result: Dict, timeout: int):
        """Wait for expected result after form submission or action."""
        result_type = expected_result.get("type", "success")
        
        try:
            if result_type == "redirect":
                url_contains = expected_result.get("url_contains", "")
                await page.wait_for_url(f"*{url_contains}*", timeout=timeout * 1000)
                self.log(f"Redirected to URL containing: {url_contains}")
            
            elif result_type == "error":
                error_contains = expected_result.get("error_contains", "")
                if error_contains:
                    # Wait for error message to appear
                    await page.wait_for_selector(f"text={error_contains}", timeout=timeout * 1000)
                    self.log(f"Error message found: {error_contains}")
            
            elif result_type == "success":
                success_message = expected_result.get("success_message", "")
                if success_message:
                    await page.wait_for_selector(f"text={success_message}", timeout=timeout * 1000)
                    self.log(f"Success message found: {success_message}")
            
            # Additional wait for page to stabilize
            await page.wait_for_timeout(500)
            
        except Exception as e:
            raise Exception(f"Expected result not achieved: {e}")
    
    async def _capture_screenshot(self, page: Page, route: str, test_name: str) -> Optional[str]:
        """Capture screenshot of current page state."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_route = route.replace("/", "_").replace("\\", "_")
            safe_test = test_name.replace(" ", "_").replace("/", "_")
            filename = f"{safe_route}_{safe_test}_{timestamp}.png"
            screenshot_path = self.screenshots_dir / filename
            
            await page.screenshot(path=str(screenshot_path))
            return str(screenshot_path)
            
        except Exception as e:
            self.log(f"Failed to capture screenshot: {e}", level="WARN")
            return None
    
    async def _cleanup(self):
        """Clean up browser resources."""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            self.log("Playwright UI runner cleanup completed")
            
        except Exception as e:
            self.log(f"Error during cleanup: {e}", level="WARN")
    
    def log(self, message: str, level: str = "INFO"):
        """Add log entry."""
        timestamp = datetime.utcnow().isoformat() + "Z"
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.logs.append(log_entry)
        print(log_entry)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of test results."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["status"] == "PASS")
        failed_tests = sum(1 for r in self.results if r["status"] == "FAIL")
        total_points = sum(r.get("points", 0) for r in self.results)
        earned_points = sum(r.get("points", 0) for r in self.results if r["status"] == "PASS")
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "total_points": total_points,
            "earned_points": earned_points,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "results": self.results,
            "logs": self.logs
        }

# Convenience function for easy integration
async def run_ui_validation(base_url: str, rules_file: str) -> List[Dict[str, Any]]:
    """
    Run UI validation with Playwright.
    
    Args:
        base_url: Base URL of the Flask application
        rules_file: Path to JSON rules file containing ui_tests
        
    Returns:
        List of test results
    """
    runner = PlaywrightUIRunner(base_url)
    return await runner.run_ui_validation(rules_file)
