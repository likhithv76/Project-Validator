import os
import json
import tempfile
import zipfile
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

try:
    from .flexible_validator import FlexibleFlaskValidator
    from .playwright_runner import PlaywrightUIRunner
except ImportError:
    # Fallback for when running as standalone
    from flexible_validator import FlexibleFlaskValidator
    from playwright_runner import PlaywrightUIRunner


class TaskValidator:
    """
    Task-based validator that can validate individual tasks with both static and dynamic validation.
    Integrates with existing FlexibleFlaskValidator and PlaywrightUIRunner.
    """
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.tasks_file = self.project_root / "streamlit_app" / "rules" / "tasks.json"
        self.logs_dir = self.project_root / "Logs"
        self.tasks_config = self._load_tasks_config()
    
    # ----- Configuration injection -----
    def load_project_config(self, config_or_path) -> None:
        """Override tasks configuration at runtime with a dict or a JSON file path.
        Useful for Student UI to use the selected project's JSON instead of default tasks.json.
        """
        try:
            if isinstance(config_or_path, (str, os.PathLike)):
                p = Path(config_or_path)
                with open(p, 'r', encoding='utf-8') as f:
                    self.tasks_config = json.load(f)
            elif isinstance(config_or_path, dict):
                self.tasks_config = config_or_path
            else:
                raise ValueError("config_or_path must be a dict or path to JSON")
        except Exception as e:
            # Fall back to existing config on error
            print(f"Error loading provided project config: {e}")
    
    def set_tasks(self, tasks_list) -> None:
        """Directly replace tasks in current config."""
        base = self.tasks_config if isinstance(self.tasks_config, dict) else {}
        base.setdefault("project", "Unknown")
        base["tasks"] = list(tasks_list or [])
        self.tasks_config = base
        
    def _load_tasks_config(self) -> Dict:
        """Load tasks configuration from JSON file."""
        try:
            if self.tasks_file.exists():
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {"project": "Unknown", "tasks": []}
        except Exception as e:
            print(f"Error loading tasks config: {e}")
            return {"project": "Unknown", "tasks": []}
    
    def get_task(self, task_id: int) -> Optional[Dict]:
        """Get task configuration by ID."""
        for task in self.tasks_config.get("tasks", []):
            if task.get("id") == task_id:
                return task
        return None
    
    def get_all_tasks(self) -> List[Dict]:
        """Get all available tasks."""
        return self.tasks_config.get("tasks", [])
    
    def validate_task(self, task_id: int, project_zip_path: str, student_id: str = "anonymous") -> Dict:
        """
        Validate a specific task against uploaded project.
        
        Args:
            task_id: ID of the task to validate
            project_zip_path: Path to uploaded ZIP file
            student_id: Student identifier for logging
            
        Returns:
            Dictionary with validation results
        """
        task = self.get_task(task_id)
        if not task:
            return {
                "success": False,
                "error": f"Task {task_id} not found",
                "task_id": task_id,
                "student_id": student_id
            }
        
        # Create student-specific log directory
        student_logs_dir = self.logs_dir / student_id / f"task_{task_id}"
        student_logs_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = student_logs_dir / f"validation_{timestamp}.log"
        json_file = student_logs_dir / f"validation_{timestamp}.json"
        
        # Extract project to temporary directory
        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(project_zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Run static validation
            static_results = self._run_static_validation(task, temp_dir, log_file)
            
            # Run Playwright validation if configured
            playwright_results = self._run_playwright_validation(task, temp_dir, student_logs_dir)
            
            # Calculate total score
            total_score = static_results.get("score", 0) + playwright_results.get("score", 0)
            max_score = static_results.get("max_score", 0) + playwright_results.get("max_score", 0)
            
            # Determine if task passed
            min_score = task.get("unlock_condition", {}).get("min_score", 0)
            # Task passes if static validation succeeds and meets minimum score
            static_success = static_results.get("success", False)
            task_passed = static_success and total_score >= min_score
            
            # Compile detailed error messages
            error_messages = []
            if not static_results.get("success", False):
                error_messages.extend(static_results.get("error_details", []))
            if not playwright_results.get("success", False):
                if playwright_results.get("message"):
                    error_messages.append(playwright_results["message"])
            
            # Create comprehensive error message
            if error_messages:
                detailed_message = "Validation failed: " + "; ".join(error_messages)
            elif task_passed:
                detailed_message = "Validation completed successfully"
            else:
                detailed_message = f"Validation failed: Score {total_score}/{max_score} below required {min_score}"
            
            # Compile results
            results = {
                "success": task_passed,
                "task_id": task_id,
                "task_name": task["name"],
                "student_id": student_id,
                "timestamp": timestamp,
                "static_validation": static_results,
                "playwright_validation": playwright_results,
                "total_score": total_score,
                "max_score": max_score,
                "min_required": min_score,
                "task_passed": task_passed,
                "log_file": str(log_file),
                "json_file": str(json_file),
                "screenshots": playwright_results.get("screenshots", []),
                "message": detailed_message,
                "error_details": error_messages,
                "error": None  # Add explicit error field
            }
            
            # Save results to JSON
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            
            return results
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"ERROR in task validation: {str(e)}")
            print(f"Traceback: {error_details}")
            return {
                "success": False,
                "error": f"Task validation failed: {str(e)}",
                "task_id": task_id,
                "student_id": student_id,
                "traceback": error_details
            }
        finally:
            # Clean up temporary directory
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
    
    def _run_static_validation(self, task: Dict, project_path: str, log_file: Path) -> Dict:
        """Run static validation using FlexibleFlaskValidator."""
        try:
            # Handle both single rule and multiple rules
            validation_rules = task["validation_rules"]
            if isinstance(validation_rules, list):
                rules_list = validation_rules
            else:
                rules_list = [validation_rules]
            
            # Create a temporary rules file for this specific task
            task_rules = {
                "rules": rules_list,
                "ui_tests": []
            }
            
            temp_rules_file = Path(project_path) / "temp_task_rules.json"
            with open(temp_rules_file, 'w', encoding='utf-8') as f:
                json.dump(task_rules, f, indent=2)
            
            # Run validation
            validator = FlexibleFlaskValidator(project_path, rules_file=str(temp_rules_file))
            
            validator.log_file = log_file
            validator.json_file = log_file.parent / f"{log_file.stem}.json"
            
            validator.execute_json_rules()
            
            # Calculate score
            total_checks = validator.total_checks
            passed_checks = validator.checks_passed
            score = sum(result.get("points", 0) for result in validator.validation_results if result.get("passed", False))
            max_score = sum(result.get("points", 0) for result in validator.validation_results)
            
            try:
                temp_rules_file.unlink()
            except Exception:
                pass
            
            # Extract detailed error messages from validation results
            error_messages = []
            for result in validator.validation_results:
                if not result.get("passed", False) and result.get("message"):
                    error_messages.append(result["message"])
            
            # Create a comprehensive error message
            if error_messages:
                detailed_message = "Validation failed: " + "; ".join(error_messages)
            else:
                detailed_message = "Validation completed"
            
            return {
                "success": len(validator.errors) == 0,
                "score": score,
                "max_score": max_score,
                "checks_passed": passed_checks,
                "total_checks": total_checks,
                "errors": validator.errors,
                "warnings": validator.warnings,
                "validation_results": validator.validation_results,
                "message": detailed_message,
                "error_details": error_messages
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "score": 0,
                "max_score": 0,
                "checks_passed": 0,
                "total_checks": 0,
                "errors": [str(e)],
                "warnings": [],
                "validation_results": []
            }
    
    def _run_playwright_validation(self, task: Dict, project_path: str, logs_dir: Path) -> Dict:
        """Run Playwright validation for the task."""
        playwright_config = task.get("playwright_test")
        if not playwright_config:
            return {
                "success": True,
                "score": 0,
                "max_score": 0,
                "message": "No Playwright test configured for this task",
                "screenshots": []
            }
        
        try:
            # Start Flask app in background
            flask_process = self._start_flask_app(project_path)
            if not flask_process:
                return {
                    "success": False,
                    "error": "Failed to start Flask application",
                    "score": 0,
                    "max_score": 0,
                    "screenshots": []
                }
            
            try:
                # Wait for app to be ready
                if not self._wait_for_flask_app():
                    return {
                        "success": False,
                        "error": "Flask application did not start properly",
                        "score": 0,
                        "max_score": 0,
                        "screenshots": []
                    }
                
                # Run Playwright test
                base_url = "http://127.0.0.1:5000"
                route = playwright_config.get("route", "/")
                test_url = f"{base_url}{route}"
                
                # Create screenshots directory
                screenshots_dir = logs_dir / "screenshots"
                screenshots_dir.mkdir(exist_ok=True)
                
                # Run the test
                result = self._execute_playwright_test(
                    test_url, 
                    playwright_config, 
                    screenshots_dir,
                    task["name"]
                )
                
                return result
                
            finally:
                # Stop Flask app
                self._stop_flask_app(flask_process)
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Playwright validation failed: {str(e)}",
                "score": 0,
                "max_score": 0,
                "screenshots": []
            }
    
    def _start_flask_app(self, project_path: str) -> Optional[subprocess.Popen]:
        """Start Flask application in background process."""
        try:
            # Find main app file
            app_files = list(Path(project_path).glob("*.py"))
            main_app = None
            for app_file in app_files:
                if app_file.name in ["app.py", "main.py", "server.py"]:
                    main_app = app_file
                    break
            
            if not main_app:
                return None
            
            # Start Flask app
            cmd = ["python", str(main_app)]
            process = subprocess.Popen(
                cmd,
                cwd=project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            return process
            
        except Exception as e:
            print(f"Error starting Flask app: {e}")
            return None
    
    def _wait_for_flask_app(self, timeout: int = 10) -> bool:
        """Wait for Flask app to be ready."""
        import requests
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get("http://127.0.0.1:5000", timeout=2)
                if response.status_code == 200:
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        
        return False
    
    def _stop_flask_app(self, process: subprocess.Popen):
        """Stop Flask application process."""
        try:
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        except Exception as e:
            print(f"Error stopping Flask app: {e}")
    
    def _execute_playwright_test(self, test_url: str, config: Dict, screenshots_dir: Path, task_name: str) -> Dict:
        """Execute Playwright test based on configuration."""
        try:
            from playwright.sync_api import sync_playwright
            import asyncio
            import sys
            
            # Handle Windows asyncio compatibility
            if sys.platform == "win32":
                try:
                    # Try to set the event loop policy for Windows
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                except Exception:
                    # If that fails, try the default policy
                    pass
            
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--force-device-scale-factor=2',  # Higher DPI for crisp screenshots
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor'
                    ]
                )
                page = browser.new_page(
                    viewport={'width': 1920, 'height': 1080},  # High resolution viewport
                    device_scale_factor=2  # 2x scaling for better quality
                )
                
                # Navigate to test URL and keep initial response
                print(f"[Playwright] Navigating to: {test_url}")
                nav_response = page.goto(test_url)
                print(f"[Playwright] Navigation response: {nav_response.status if nav_response else 'No response'}")
                
                # Wait for page to be fully loaded for better screenshots
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(1000)  # Additional wait for any animations
                
                screenshots = []
                score = 0
                
                # Take initial screenshot to verify navigation
                initial_screenshot = screenshots_dir / "initial.png"
                page.screenshot(path=str(initial_screenshot), full_page=True, type='png')
                screenshots.append(str(initial_screenshot))
                print(f"[Playwright] Initial screenshot saved: {initial_screenshot}")
                max_score = config.get("points", 0)
                errors = []
                
                # Execute actions
                actions = config.get("actions", [])
                print(f"[Playwright] Executing {len(actions)} actions")
                for i, action in enumerate(actions):
                    try:
                        # Skip invalid entries
                        if not isinstance(action, dict):
                            continue
                        
                        print(f"[Playwright] Action {i+1}: {action}")
                        
                        def build_selector(a: Dict) -> str:
                            st = a.get("selector_type", "class")
                            sv = a.get("selector_value", "")
                            if st == "css":
                                return sv
                            if st == "id":
                                return f"#{sv}"
                            if st == "name":
                                return f"[name=\"{sv}\"]"
                            if st == "type":
                                return f"[type=\"{sv}\"]"
                            # default: class
                            return f".{sv}"
                        
                        if action.get("input"):
                            # Fill input field
                            selector = build_selector(action)
                            page.fill(selector, action["input"])
                            
                        elif action.get("click"):
                            # Click element
                            selector = build_selector(action)
                            print(f"[Playwright] Clicking selector '{selector}'")
                            
                            # Check if element exists before clicking
                            element = page.locator(selector)
                            if element.count() == 0:
                                print(f"[Playwright] Click element not found: {selector}")
                                errors.append(f"Click element {action['selector_value']} not found")
                            else:
                                page.click(selector)
                                print(f"[Playwright] Successfully clicked {selector}")
                            
                        elif action.get("input_variants"):
                            # Try the first non-empty variant
                            variants = action.get("input_variants", [])
                            to_fill = None
                            for v in variants:
                                if isinstance(v, str) and v is not None:
                                    to_fill = v
                                    break
                            if to_fill is None:
                                to_fill = ""
                            selector = build_selector(action)
                            print(f"[Playwright] Filling selector '{selector}' with value '{to_fill}'")
                            
                            # Check if element exists before filling
                            element = page.locator(selector)
                            if element.count() == 0:
                                print(f"[Playwright] Element not found: {selector}")
                                errors.append(f"Element {action['selector_value']} not found")
                            else:
                                page.fill(selector, to_fill)
                                print(f"[Playwright] Successfully filled {selector}")
                            
                        # Wait for any UI updates after action
                        page.wait_for_timeout(500)
                        
                        if action.get("check_type") == "exists":
                            # Check if element exists
                            selector = build_selector(action)
                            element = page.locator(selector)
                            if not element.count():
                                errors.append(f"Element {action['selector_value']} not found")
                        
                        # Take high-quality screenshot after each action
                        screenshot_path = screenshots_dir / f"step_{i+1}.png"
                        try:
                            page.screenshot(
                                path=str(screenshot_path),
                                full_page=True,  # Capture entire page
                                type='png'       # PNG format for better quality
                            )
                            screenshots.append(str(screenshot_path))
                        except Exception as e:
                            errors.append(f"Screenshot capture failed: {str(e)}")
                        
                    except Exception as e:
                        errors.append(f"Action {i+1} failed: {str(e)}")
                
                # Validate results
                validations = config.get("validate", [])
                for validation in validations:
                    try:
                        if not isinstance(validation, dict):
                            continue
                        vtype = validation.get("type")
                        if vtype == "text_present":
                            text_value = validation["value"]
                            tag = validation.get("tag")
                            
                            if tag:
                                # Check text within specific HTML tag
                                try:
                                    elements = page.locator(tag).all()
                                    found = False
                                    for element in elements:
                                        element_text = element.text_content()
                                        if text_value in element_text:
                                            found = True
                                            break
                                    
                                    if not found:
                                        errors.append(f"Expected text '{text_value}' not found in <{tag}> elements")
                                    else:
                                        score += validation.get("points", 0)
                                except Exception as e:
                                    errors.append(f"Error checking text in <{tag}>: {str(e)}")
                            else:
                                # Check text anywhere in page content (original behavior)
                                content = page.content()
                                if text_value not in content:
                                    errors.append(f"Expected text '{text_value}' not found")
                                else:
                                    score += validation.get("points", 0)
                        
                        elif vtype == "url_redirect":
                            current_url = page.url
                            if validation["value"] not in current_url:
                                errors.append(f"Expected URL '{validation['value']}' not found in {current_url}")
                            else:
                                score += validation.get("points", 0)
                        
                        elif vtype == "status_code":
                            try:
                                expected = int(validation.get("value", 200))
                            except Exception:
                                expected = 200
                            status = None
                            if nav_response is not None:
                                try:
                                    attr = getattr(nav_response, "status", None)
                                    status = attr() if callable(attr) else attr
                                except Exception:
                                    status = None
                            if status != expected:
                                errors.append(f"Unexpected status code: {status} (expected {expected})")
                            else:
                                score += validation.get("points", 0)
                                
                    except Exception as e:
                        errors.append(f"Validation failed: {str(e) or type(e).__name__}")
                
                # Take high-quality final screenshot
                final_screenshot = screenshots_dir / "final.png"
                try:
                    page.screenshot(
                        path=str(final_screenshot),
                        full_page=True,  # Capture entire page
                        type='png'       # PNG format for better quality
                    )
                    screenshots.append(str(final_screenshot))
                except Exception as e:
                    errors.append(f"Final screenshot capture failed: {str(e)}")
                
                browser.close()
                
                success = len(errors) == 0
                if success:
                    score = max_score  # Award full points if all validations pass
                
                return {
                    "success": success,
                    "score": score,
                    "max_score": max_score,
                    "errors": errors,
                    "screenshots": screenshots,
                    "message": "UI test completed successfully" if success else f"UI test failed: {'; '.join(errors)}"
                }
                
        except NotImplementedError as e:
            return {
                "success": False,
                "error": f"Playwright not supported on this platform: {str(e)}. Please ensure Playwright is properly installed with 'playwright install'.",
                "score": 0,
                "max_score": 0,
                "screenshots": [],
                "errors": [str(e)]
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Playwright execution failed: {str(e)}",
                "score": 0,
                "max_score": 0,
                "screenshots": [],
                "errors": [str(e)]
            }
    
    def get_student_progress(self, student_id: str, project_id: str = None) -> Dict:
        """Get student's progress across all tasks for a specific project."""
        if project_id:
            progress_file = self.logs_dir / student_id / f"progress_{project_id}.json"
        else:
            progress_file = self.logs_dir / student_id / "progress.json"
        
        if progress_file.exists():
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Return default progress
        return {
            "student_id": student_id,
            "project_id": project_id,
            "completed_tasks": [],
            "current_task": 1,
            "total_score": 0,
            "last_updated": datetime.now().isoformat()
        }
    
    def update_student_progress(self, student_id: str, task_result: Dict, project_id: str = None):
        """Update student's progress after task completion for a specific project."""
        progress = self.get_student_progress(student_id, project_id)
        
        task_id = task_result["task_id"]
        task_passed = task_result["task_passed"]
        
        if task_passed and task_id not in progress["completed_tasks"]:
            progress["completed_tasks"].append(task_id)
            progress["total_score"] += task_result["total_score"]
        
        # Update current task to next unlocked task
        all_tasks = self.get_all_tasks()
        for task in all_tasks:
            required_tasks = task.get("unlock_condition", {}).get("required_tasks", [])
            if all(rt in progress["completed_tasks"] for rt in required_tasks):
                if task["id"] not in progress["completed_tasks"]:
                    progress["current_task"] = task["id"]
                    break
        
        progress["last_updated"] = datetime.now().isoformat()
        
        # Save progress with project-specific filename
        if project_id:
            progress_file = self.logs_dir / student_id / f"progress_{project_id}.json"
        else:
            progress_file = self.logs_dir / student_id / "progress.json"
        
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2)
        
        return progress
