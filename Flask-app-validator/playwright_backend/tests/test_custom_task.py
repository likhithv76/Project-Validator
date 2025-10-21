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
        
        # Navigate to the route
        full_url = f"{base_url}{route}" if not route.startswith("http") else route
        await page.goto(full_url, timeout=10000)
        
        # Take initial screenshot
        await page.screenshot(path="initial_page.png")
        
        # Execute actions
        for action in actions:
            await execute_action(page, action)
        
        # Take final screenshot after actions
        await page.screenshot(path="after_actions.png")
        
        # Validate results
        validation_results = []
        for validation_rule in validate:
            result = await validate_rule(page, validation_rule)
            validation_results.append(result)
        
        # Return results
        return {
            "status": "PASS" if all(r["passed"] for r in validation_results) else "FAIL",
            "validation_results": validation_results,
            "screenshots": ["initial_page.png", "after_actions.png"]
        }
        
    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "screenshots": []
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

async def validate_rule(page: Page, rule: dict):
    """Validate a single rule on the page."""
    rule_type = rule.get("type", "unknown")
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
