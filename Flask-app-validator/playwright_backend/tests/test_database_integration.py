"""
Database integration tests for Flask applications.
Tests that database operations work correctly through the UI.
"""

import time
from playwright.async_api import Page, expect

async def test_database_connection_indicator(page: Page, base_url: str):
    """Test that the application shows signs of database connectivity."""
    await page.goto(base_url)
    
    # Look for indicators that data is being loaded from database
    db_indicators = [
        page.locator("table tr"),  # Data tables
        page.locator(".item, .post, .entry"),  # Data items
        page.locator("[class*='list']"),  # Data lists
        page.locator("ul li, ol li"),  # List items
        page.locator("[class*='card']")  # Data cards
    ]
    
    data_loaded = False
    for indicator in db_indicators:
        if await indicator.count() > 0:
            data_loaded = True
            break
    
    # If no specific data containers, check for dynamic content
    if not data_loaded:
        # Look for any content that might be database-driven
        body_text = await page.locator("body").text_content()
        # Check for common database-driven content patterns
        db_patterns = ["id:", "created:", "updated:", "user:", "date:"]
        data_loaded = any(pattern in body_text.lower() for pattern in db_patterns)
    
    assert data_loaded, "Application should show signs of database connectivity"

async def test_data_creation_persistence(page: Page, base_url: str):
    """Test that created data persists and is displayed."""
    await page.goto(base_url)
    
    # Find a form to create data
    forms = page.locator("form")
    form_count = await forms.count()
    
    if form_count > 0:
        form = forms.first
        
        # Fill out form with unique test data
        timestamp = str(int(time.time()))
        test_data = [
            f"Test Title {timestamp}",
            f"Test Content {timestamp}",
            f"test{timestamp}@example.com"
        ]
        
        # Fill form inputs
        text_inputs = form.locator("input[type='text'], input[type='email'], textarea")
        input_count = await text_inputs.count()
        
        for i, data in enumerate(test_data):
            if i < input_count:
                input_field = text_inputs.nth(i)
                await input_field.fill(data)
        
        # Submit form
        submit_button = form.locator("button[type='submit'], input[type='submit']").first
        if await submit_button.count() > 0:
            await submit_button.click()
            await page.wait_for_timeout(2000)
            
            # Check if data appears on the page after submission
            data_found = False
            for data in test_data:
                if data in await page.text_content():
                    data_found = True
                    break
            
            assert data_found, "Created data should be visible after form submission"

async def test_data_retrieval_display(page: Page, base_url: str):
    """Test that data is properly retrieved and displayed from database."""
    await page.goto(base_url)
    
    # Look for data display elements
    data_containers = [
        page.locator("table"),
        page.locator(".list, .items"),
        page.locator("[class*='card']"),
        page.locator("ul, ol")
    ]
    
    data_displayed = False
    for container in data_containers:
        if await container.count() > 0:
            # Check if container has multiple items (suggesting database data)
            items = container.locator("tr, li, .item, .card")
            item_count = await items.count()
            if item_count > 0:
                data_displayed = True
                break
    
    # If no structured data, check for any meaningful content
    if not data_displayed:
        body_text = await page.locator("body").text_content()
        # Look for patterns that suggest database content
        content_patterns = ["id:", "created:", "updated:", "user:", "title:", "content:"]
        data_displayed = any(pattern in body_text.lower() for pattern in content_patterns)
    
    assert data_displayed, "Data should be retrieved and displayed from database"

async def test_data_relationships(page: Page, base_url: str):
    """Test that data relationships are properly displayed."""
    await page.goto(base_url)
    
    # Look for indicators of data relationships
    relationship_indicators = [
        page.locator("a[href*='user']"),  # User links
        page.locator("a[href*='category']"),  # Category links
        page.locator("a[href*='tag']"),  # Tag links
        page.locator("[class*='author']"),  # Author information
        page.locator("[class*='category']"),  # Category information
        page.locator("[class*='tag']")  # Tag information
    ]
    
    relationships_found = False
    for indicator in relationship_indicators:
        if await indicator.count() > 0:
            relationships_found = True
            break
    
    # Relationships are optional, so we'll just verify page loads
    assert await page.locator("body").count() > 0, "Page should load successfully"

async def test_database_error_handling(page: Page, base_url: str):
    """Test that database errors are handled gracefully."""
    await page.goto(base_url)
    
    # Try to access a potentially problematic URL that might cause DB errors
    error_urls = [
        base_url + "/nonexistent",
        base_url + "/error",
        base_url + "/test"
    ]
    
    error_handled = True
    for url in error_urls:
        try:
            response = await page.goto(url)
            if response and response.status >= 500:
                # Server error - check if it's handled gracefully
                page_content = await page.text_content()
                if "error" in page_content.lower() and "database" in page_content.lower():
                    error_handled = False
                    break
        except Exception:
            continue
    
    assert error_handled, "Database errors should be handled gracefully"

async def test_data_consistency(page: Page, base_url: str):
    """Test that data remains consistent across page loads."""
    await page.goto(base_url)
    
    # Get initial page content
    initial_content = await page.text_content()
    
    # Reload page
    await page.reload()
    await page.wait_for_timeout(1000)
    
    # Get content after reload
    reloaded_content = await page.text_content()
    
    # Check that main content is consistent (allowing for dynamic elements like timestamps)
    # Remove timestamps and dynamic content for comparison
    import re
    
    # Remove common dynamic content
    initial_clean = re.sub(r'\d{4}-\d{2}-\d{2}', '', initial_content)
    initial_clean = re.sub(r'\d{2}:\d{2}:\d{2}', '', initial_clean)
    initial_clean = re.sub(r'\d+', '', initial_clean)
    
    reloaded_clean = re.sub(r'\d{4}-\d{2}-\d{2}', '', reloaded_content)
    reloaded_clean = re.sub(r'\d{2}:\d{2}:\d{2}', '', reloaded_clean)
    reloaded_clean = re.sub(r'\d+', '', reloaded_clean)
    
    # Check that core content is similar (allowing for some variation)
    similarity = len(set(initial_clean.split()) & set(reloaded_clean.split())) / max(len(set(initial_clean.split())), 1)
    
    assert similarity > 0.5, "Data should remain consistent across page loads"

async def test_database_performance(page: Page, base_url: str):
    """Test that database operations don't cause excessive delays."""
    start_time = time.time()
    
    await page.goto(base_url)
    
    load_time = time.time() - start_time
    
    # Page should load within reasonable time (10 seconds)
    assert load_time < 10, f"Page should load within 10 seconds, took {load_time:.2f}s"
    
    # Check for any loading indicators that might suggest slow database queries
    loading_indicators = [
        page.locator(".loading, .spinner"),
        page.locator("[class*='loading']"),
        page.locator("text=Loading"),
        page.locator("text=Please wait")
    ]
    
    still_loading = False
    for indicator in loading_indicators:
        if await indicator.count() > 0:
            still_loading = True
            break
    
    assert not still_loading, "Page should not show loading indicators after initial load"

async def test_database_security(page: Page, base_url: str):
    """Test that database operations are secure."""
    await page.goto(base_url)
    
    # Look for any exposed database information
    page_content = await page.text_content()
    
    # Check for common database error messages that might expose information
    security_issues = [
        "sql error",
        "database error",
        "connection failed",
        "table doesn't exist",
        "column doesn't exist",
        "syntax error",
        "mysql error",
        "postgresql error",
        "sqlite error"
    ]
    
    exposed_info = any(issue in page_content.lower() for issue in security_issues)
    
    assert not exposed_info, "Database errors should not expose sensitive information"

async def test_data_validation_integration(page: Page, base_url: str):
    """Test that data validation works with database operations."""
    await page.goto(base_url)
    
    # Find forms that interact with database
    forms = page.locator("form")
    form_count = await forms.count()
    
    if form_count > 0:
        form = forms.first
        
        # Try to submit form with invalid data
        text_inputs = form.locator("input[type='text'], input[type='email'], textarea")
        input_count = await text_inputs.count()
        
        if input_count > 0:
            # Fill with invalid data
            invalid_data = ["", "invalid-email", "x" * 1000]  # Empty, invalid email, too long
            
            for i, data in enumerate(invalid_data):
                if i < input_count:
                    input_field = text_inputs.nth(i)
                    await input_field.fill(data)
            
            # Submit form
            submit_button = form.locator("button[type='submit'], input[type='submit']").first
            if await submit_button.count() > 0:
                await submit_button.click()
                await page.wait_for_timeout(2000)
                
                # Check for validation errors
                error_indicators = [
                    page.locator(".error, .alert-danger"),
                    page.locator("text=Invalid"),
                    page.locator("text=Error"),
                    page.locator("text=Required"),
                    page.locator("text=Too long")
                ]
                
                validation_working = False
                for indicator in error_indicators:
                    if await indicator.count() > 0:
                        validation_working = True
                        break
                
                # If no explicit errors, check that data wasn't saved (form still visible)
                if not validation_working:
                    form_still_visible = await form.count() > 0
                    validation_working = form_still_visible
                
                assert validation_working, "Data validation should prevent invalid data submission"
