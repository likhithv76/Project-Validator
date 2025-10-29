import asyncio
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

class PlaywrightTestRunner:   
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.logs = []
        self.results_dir = Path(__file__).parent / "results"
        # Allow overriding results target base via env for creator runs
        override = os.environ.get("CREATOR_RESULTS_DIR")
        if override:
            self.results_dir = Path(override)
        self.tests_dir = Path(__file__).parent / "tests"
        
    async def initialize(self):
        try:
            self.playwright = await async_playwright().start()
            self.log(f"Playwright initialized successfully")
        except Exception as e:
            self.log(f"Failed to initialize Playwright: {e}", level="ERROR")
            raise
    
    async def run_custom_task_test(
        self,
        base_url: str,
        task_config: dict,
        project_name: str = "custom_task",
        timeout: int = 30,
        headless: bool = True,
        capture_screenshots: bool = True,
        results_base_dir: Optional[str] = None
    ) -> List[Dict]:
        """
        Run a custom task test based on provided configuration.
        
        Args:
            base_url: Base URL of the Flask application
            task_config: Task configuration with route, actions, and validation rules
            project_name: Name of the project being tested
            timeout: Test timeout in seconds
            headless: Run browser in headless mode
            capture_screenshots: Capture screenshots on failures
            
        Returns:
            List of test results
        """
        start_time = time.time()
        results = []
        
        try:
            base_dir = Path(results_base_dir) if results_base_dir else self.results_dir
            project_results_dir = base_dir / project_name
            project_results_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize browser if not already done
            if not self.playwright or not self.browser:
                await self._launch_browser(headless=headless)
            
            # Import custom task test
            from tests.test_custom_task import test_custom_task, test_screenshot_capture
            
            # Run the custom task test
            page = await self.context.new_page()
            
            if task_config.get("screenshot_only", False):
                # Just capture screenshot
                result = await test_screenshot_capture(page, base_url, task_config)
            else:
                # Run full test
                result = await test_custom_task(page, base_url, task_config)
            
            await page.close()
            
            # Format result with more detail
            validation_results = result.get("validation_results", [])
            validation_count = len(validation_results)
            passed_validations = sum(1 for v in validation_results if v.get("passed", False))
            
            test_result = {
                "name": f"Task {task_config.get('task_id', 'Unknown')}",
                "status": result.get("status", "UNKNOWN"),
                "duration": time.time() - start_time,
                "error": result.get("error"),
                "screenshot": result.get("reference_screenshot") or result.get("screenshot"),
                "validation_results": validation_results,
                "validation_count": validation_count,
                "passed_validations": passed_validations,
                "action_logs": result.get("action_logs", []),
                "comprehensive_test": result.get("comprehensive_test", False)
            }
            
            results.append(test_result)
            
            # Save screenshots if captured
            if capture_screenshots and result.get("screenshots"):
                screenshots_dir = project_results_dir / "screenshots"
                screenshots_dir.mkdir(exist_ok=True)
                
                for i, screenshot in enumerate(result["screenshots"]):
                    if screenshot and os.path.exists(screenshot):
                        # Copy screenshot to results directory
                        new_path = screenshots_dir / f"screenshot_{i}.png"
                        # Remove existing file if it exists
                        if new_path.exists():
                            new_path.unlink()
                        shutil.copy(screenshot, new_path)
                        test_result[f"screenshot_{i}"] = str(new_path)
                        # Clean up the original screenshot
                        try:
                            os.remove(screenshot)
                        except:
                            pass
            
            await self._save_results(project_results_dir, results, start_time)
            
        except Exception as e:
            self.log(f"Error during custom task test execution: {e}", level="ERROR")
            results.append({
                "name": f"Task {task_config.get('task_id', 'Unknown')}",
                "status": "FAIL",
                "duration": time.time() - start_time,
                "error": str(e)
            })
        
        # Don't cleanup browser here - let it stay alive for multiple tests
        # await self._cleanup()
        
        return results

    async def run_tests(
        self,
        base_url: str,
        test_suite: str = "default",
        project_name: str = "student_project",
        timeout: int = 30,
        headless: bool = True,
        capture_screenshots: bool = True
    ) -> List[Dict]:
        """
        Run UI tests on the specified Flask application.
        
        Args:
            base_url: Base URL of the Flask application
            test_suite: Test suite to run (default, auth, crud, etc.)
            project_name: Name of the project being tested
            timeout: Test timeout in seconds
            headless: Run browser in headless mode
            capture_screenshots: Capture screenshots on failures
            
        Returns:
            List of test results
        """
        start_time = time.time()
        results = []
        
        try:
            project_results_dir = self.results_dir / project_name
            project_results_dir.mkdir(parents=True, exist_ok=True)
            
            await self._launch_browser(headless=headless)
            
            test_files = self._discover_tests(test_suite)
            self.log(f"Found {len(test_files)} test files for suite: {test_suite}")
            
            for test_file in test_files:
                self.log(f"Running tests from: {test_file.name}")
                file_results = await self._run_test_file(
                    test_file, base_url, timeout, capture_screenshots, project_results_dir
                )
                results.extend(file_results)
            
            await self._save_results(project_results_dir, results, start_time)
            
        except Exception as e:
            self.log(f"Error during test execution: {e}", level="ERROR")
            results.append({
                "name": "Test Execution Error",
                "status": "FAIL",
                "duration": time.time() - start_time,
                "error": str(e)
            })
        
        finally:
            await self._cleanup()
        
        return results
    
    async def _launch_browser(self, headless: bool = True):
        try:
            if not self.playwright:
                raise Exception("Playwright not initialized")
            
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding"
                ]
            )
            
            if not self.browser:
                raise Exception("Failed to create browser instance")
            
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            
            if not self.context:
                raise Exception("Failed to create browser context")
            
            self.log("Browser launched successfully")
            
        except Exception as e:
            self.log(f"Failed to launch browser: {e}", level="ERROR")
            await self._cleanup()
            raise
    
    def _discover_tests(self, test_suite: str) -> List[Path]:
        if not self.tests_dir.exists():
            self.log("Tests directory not found", level="WARN")
            return []
        
        if test_suite == "default":
            test_files = list(self.tests_dir.glob("test_*.py"))
        else:
            test_files = list(self.tests_dir.glob(f"test_{test_suite}*.py"))
        
        return test_files
    
    async def _run_test_file(
        self,
        test_file: Path,
        base_url: str,
        timeout: int,
        capture_screenshots: bool,
        results_dir: Path
    ) -> List[Dict]:
        results = []
        
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("test_module", test_file)
            test_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(test_module)
            
            test_functions = [
                getattr(test_module, name) for name in dir(test_module)
                if name.startswith("test_") and callable(getattr(test_module, name))
            ]
            
            self.log(f"Found {len(test_functions)} test functions in {test_file.name}")
            
            for test_func in test_functions:
                result = await self._run_single_test(
                    test_func, base_url, timeout, capture_screenshots, results_dir
                )
                results.append(result)
                
        except Exception as e:
            self.log(f"Error running test file {test_file.name}: {e}", level="ERROR")
            results.append({
                "name": f"Test File Error: {test_file.name}",
                "status": "FAIL",
                "duration": 0.0,
                "error": str(e)
            })
        
        return results
    
    async def _run_single_test(
        self,
        test_func,
        base_url: str,
        timeout: int,
        capture_screenshots: bool,
        results_dir: Path
    ) -> Dict:
        """Run a single test function."""
        test_name = test_func.__name__
        start_time = time.time()
        page = None
        
        try:
            self.log(f"Running test: {test_name}")
            
            if not self.context:
                raise Exception("Browser context has been closed")
            
            page = await self.context.new_page()
            
            page.on("console", lambda msg: self.log(f"Console {msg.type}: {msg.text}"))
            page.on("pageerror", lambda error: self.log(f"Page error: {error}", level="ERROR"))
            
            await asyncio.wait_for(
                test_func(page, base_url),
                timeout=timeout
            )
            
            duration = time.time() - start_time
            self.log(f"Test {test_name} PASSED in {duration:.2f}s")
            
            if page:
                try:
                    await page.close()
                except Exception as e:
                    self.log(f"Error closing page: {e}", level="WARN")
            
            return {
                "name": test_name,
                "status": "PASS",
                "duration": duration,
                "error": None,
                "screenshot": None
            }
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            self.log(f"Test {test_name} TIMEOUT after {duration:.2f}s", level="ERROR")
            
            screenshot_path = None
            if capture_screenshots and page:
                try:
                    screenshot_path = await self._capture_screenshot(
                        page, test_name, results_dir
                    )
                except Exception as e:
                    self.log(f"Failed to capture screenshot: {e}", level="WARN")
            
            if page:
                try:
                    await page.close()
                except Exception as e:
                    self.log(f"Error closing page: {e}", level="WARN")
            
            return {
                "name": test_name,
                "status": "FAIL",
                "duration": duration,
                "error": f"Test timeout after {timeout} seconds",
                "screenshot": screenshot_path
            }
            
        except Exception as e:
            duration = time.time() - start_time
            self.log(f"Test {test_name} FAILED: {e}", level="ERROR")
            
            screenshot_path = None
            if capture_screenshots and page:
                try:
                    screenshot_path = await self._capture_screenshot(
                        page, test_name, results_dir
                    )
                except Exception as e:
                    self.log(f"Failed to capture screenshot: {e}", level="WARN")
            
            if page:
                try:
                    await page.close()
                except Exception as e:
                    self.log(f"Error closing page: {e}", level="WARN")
            
            return {
                "name": test_name,
                "status": "FAIL",
                "duration": duration,
                "error": str(e),
                "screenshot": screenshot_path
            }
    
    async def _capture_screenshot(
        self, page: Page, test_name: str, results_dir: Path
    ) -> Optional[str]:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_name = f"{test_name}_{timestamp}.png"
            screenshot_path = results_dir / "screenshots" / screenshot_name
            
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            
            await page.screenshot(path=str(screenshot_path), full_page=True)
            
            self.log(f"Screenshot saved: {screenshot_path}")
            return str(screenshot_path)
            
        except Exception as e:
            self.log(f"Failed to capture screenshot: {e}", level="WARN")
            return None
    
    async def _save_results(self, results_dir: Path, results: List[Dict], start_time: float):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = results_dir / f"test_results_{timestamp}.json"
            
            summary = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "execution_time": time.time() - start_time,
                "total_tests": len(results),
                "passed_tests": sum(1 for r in results if r["status"] == "PASS"),
                "failed_tests": sum(1 for r in results if r["status"] == "FAIL"),
                "results": results,
                "logs": self.logs
            }
            
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            
            self.log(f"Results saved to: {results_file}")
            
        except Exception as e:
            self.log(f"Failed to save results: {e}", level="ERROR")
    
    async def _cleanup(self):
        try:
            if self.context:
                try:
                    await self.context.close()
                except Exception as e:
                    self.log(f"Error closing context: {e}", level="WARN")
                self.context = None
            
            if self.browser:
                try:
                    await self.browser.close()
                except Exception as e:
                    self.log(f"Error closing browser: {e}", level="WARN")
                self.browser = None
            
            if self.playwright:
                try:
                    await self.playwright.stop()
                except Exception as e:
                    self.log(f"Error stopping playwright: {e}", level="WARN")
                self.playwright = None
            
            self.log("Browser cleanup completed")
            
        except Exception as e:
            self.log(f"Error during cleanup: {e}", level="WARN")
        finally:
            self.context = None
            self.browser = None
            self.playwright = None
    
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.utcnow().isoformat() + "Z"
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.logs.append(log_entry)
        print(log_entry)
    
    def get_logs(self) -> List[str]:
        return self.logs.copy()
