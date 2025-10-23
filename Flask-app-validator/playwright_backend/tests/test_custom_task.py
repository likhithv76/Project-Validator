"""
Custom test for task-specific Playwright validation.
This test runs based on task configuration provided by the creator.
"""

from playwright.async_api import Page, expect
import json

async def test_custom_task(page: Page, base_url: str, task_config: dict = None):
    """Test a custom task based on provided configuration."""
    try:
        # Get task configuration
        route = task_config.get("route", "/")
        actions = task_config.get("actions", [])
        validate = task_config.get("validate", [])
        comprehensive_test = task_config.get("comprehensive_test", False)
        
        # Navigate to the route
        full_url = f"{base_url}{route}" if not route.startswith("http") else route
        await page.goto(full_url, timeout=10000)
        
        # Take initial screenshot
        initial_screenshot = f"initial_task_{task_config.get('task_id', 'unknown')}.png"
        await page.screenshot(path=initial_screenshot)
        
        # Execute actions
        action_logs = []
        for i, action in enumerate(actions):
            try:
                await execute_action(page, action)
                action_logs.append(f"Action {i+1} executed successfully: {action}")
            except Exception as e:
                action_logs.append(f"Action {i+1} failed: {str(e)}")
        
        # Take final screenshot after actions
        final_screenshot = f"final_task_{task_config.get('task_id', 'unknown')}.png"
        await page.screenshot(path=final_screenshot)
        
        # Validate results
        validation_results = []
        for validation_rule in validate:
            result = await validate_rule(page, validation_rule)
            validation_results.append(result)
        
        # For comprehensive testing, also capture reference screenshot
        reference_screenshot = None
        if comprehensive_test:
            reference_screenshot = f"reference_task_{task_config.get('task_id', 'unknown')}.png"
            await page.screenshot(path=reference_screenshot)
        
        # Determine overall status
        all_validations_passed = all(r.get("passed", False) for r in validation_results)
        status = "PASS" if all_validations_passed else "FAIL"
        
        # Return comprehensive results
        result = {
            "status": status,
            "validation_results": validation_results,
            "screenshots": [initial_screenshot, final_screenshot],
            "action_logs": action_logs,
            "comprehensive_test": comprehensive_test
        }
        
        if reference_screenshot:
            result["screenshots"].append(reference_screenshot)
            result["reference_screenshot"] = reference_screenshot
        
        return result
        
    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "screenshots": [],
            "validation_results": [],
            "action_logs": [f"Test execution failed: {str(e)}"]
        }

async def execute_action(page: Page, action: dict):
    """Execute a single action on the page."""
    action_type = action.get("type", "unknown")
    
    if action_type == "click" or action.get("click"):
        # Click action
        selector_type = action.get("selector_type", "class")
        selector_value = action.get("selector_value", "")
        
        if selector_type == "class":
            await page.click(f".{selector_value}")
        elif selector_type == "id":
            await page.click(f"#{selector_value}")
        elif selector_type == "text":
            await page.click(f"text={selector_value}")
        else:
            await page.click(selector_value)
    
    elif action_type == "input" or action.get("input_variants"):
        # Input action
        selector_type = action.get("selector_type", "class")
        selector_value = action.get("selector_value", "")
        input_variants = action.get("input_variants", [])
        
        if input_variants:
            # Use first variant for testing
            input_value = input_variants[0]
        else:
            input_value = "test_input"
        
        if selector_type == "class":
            await page.fill(f".{selector_value}", input_value)
        elif selector_type == "id":
            await page.fill(f"#{selector_value}", input_value)
        elif selector_type == "name":
            await page.fill(f"[name='{selector_value}']", input_value)
        else:
            await page.fill(selector_value, input_value)
    
    elif action_type == "navigate":
        # Navigation action
        url = action.get("url", "/")
        await page.goto(url)
    
    # Add small delay between actions
    await page.wait_for_timeout(500)

async def validate_rule(page: Page, rule):
    """Validate a single rule on the page."""
    # Handle both dict and string rules
    if isinstance(rule, str):
        rule_type = "text_present"
        rule_value = rule
    else:
        rule_type = rule.get("type", "text_present")
        rule_value = rule.get("value", "")
    
    try:
        if rule_type == "text_present":
            # Check if text is present on the page
            content = await page.content()
            passed = rule_value.lower() in content.lower()
            return {
                "rule": f"text_present: {rule_value}",
                "passed": passed,
                "message": f"Text '{rule_value}' {'found' if passed else 'not found'}"
            }
        
        elif rule_type == "element_present":
            # Check if element is present
            selector = rule_value
            element = page.locator(selector)
            count = await element.count()
            passed = count > 0
            return {
                "rule": f"element_present: {rule_value}",
                "passed": passed,
                "message": f"Element '{rule_value}' {'found' if passed else 'not found'}"
            }
        
        elif rule_type == "title_contains":
            # Check if page title contains text
            title = await page.title()
            passed = rule_value.lower() in title.lower()
            return {
                "rule": f"title_contains: {rule_value}",
                "passed": passed,
                "message": f"Title contains '{rule_value}': {'Yes' if passed else 'No'}"
            }
        
        elif rule_type == "url_contains":
            # Check if URL contains text
            url = page.url
            passed = rule_value.lower() in url.lower()
            return {
                "rule": f"url_contains: {rule_value}",
                "passed": passed,
                "message": f"URL contains '{rule_value}': {'Yes' if passed else 'No'}"
            }
        
        else:
            # Generic text validation
            content = await page.content()
            passed = rule_value.lower() in content.lower()
            return {
                "rule": f"generic: {rule_value}",
                "passed": passed,
                "message": f"Content contains '{rule_value}': {'Yes' if passed else 'No'}"
            }
    
    except Exception as e:
        return {
            "rule": f"{rule_type}: {rule_value}",
            "passed": False,
            "message": f"Validation error: {str(e)}"
        }

async def test_screenshot_capture(page: Page, base_url: str, task_config: dict = None):
    """Capture screenshot for reference purposes."""
    try:
        route = task_config.get("route", "/")
        actions = task_config.get("actions", [])
        
        # Navigate to the route
        full_url = f"{base_url}{route}" if not route.startswith("http") else route
        await page.goto(full_url, timeout=10000)
        
        # Execute actions
        for action in actions:
            await execute_action(page, action)
        
        # Capture final screenshot
        screenshot_path = f"reference_task_{task_config.get('task_id', 'unknown')}.png"
        await page.screenshot(path=screenshot_path)
        
        return {
            "status": "PASS",
            "screenshot": screenshot_path
        }
        
    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "screenshot": None
        }
