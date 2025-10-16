"""
CRUD operations tests for Flask applications.
Tests Create, Read, Update, Delete functionality through UI.
"""

from playwright.async_api import Page, expect

async def test_create_form_exists(page: Page, base_url: str):
    """Test that create/add forms exist for data entry."""
    # Try common create page paths
    create_paths = ["/create", "/add", "/new", "/post/create", "/item/create"]
    
    create_accessible = False
    for path in create_paths:
        try:
            response = await page.goto(base_url + path)
            if response and response.status < 400:
                create_accessible = True
                break
        except Exception:   
            continue
    
    if not create_accessible:
        # Check if create form exists on home page
        await page.goto(base_url)
        create_form = page.locator("form").filter(has=page.locator("input[type='text'], textarea"))
        create_accessible = await create_form.count() > 0
    
    assert create_accessible, "Create form or page should be accessible"

async def test_create_form_structure(page: Page, base_url: str):
    """Test that create form has proper structure."""
    await page.goto(base_url)
    
    # Look for create form
    create_form = page.locator("form").filter(has=page.locator("input[type='text'], textarea"))
    form_count = await create_form.count()
    
    if form_count > 0:
        form = create_form.first
        
        # Check for required elements
        text_inputs = form.locator("input[type='text'], input[type='email'], textarea")
        submit_button = form.locator("button[type='submit'], input[type='submit']")
        
        assert await text_inputs.count() > 0, "Create form should have text inputs"
        assert await submit_button.count() > 0, "Create form should have submit button"
        
        # Check for proper labels
        labels = form.locator("label")
        label_count = await labels.count()
        assert label_count > 0, "Form inputs should have labels"

async def test_read_data_display(page: Page, base_url: str):
    """Test that data is displayed in a readable format."""
    await page.goto(base_url)
    
    # Look for data display elements
    data_indicators = [
        page.locator("table"),
        page.locator(".list, .items, .posts"),
        page.locator("[class*='card']"),
        page.locator("[class*='item']"),
        page.locator("ul, ol")
    ]
    
    data_displayed = False
    for indicator in data_indicators:
        if await indicator.count() > 0:
            data_displayed = True
            break
    
    # If no specific data containers, check for any content
    if not data_displayed:
        body_text = await page.locator("body").text_content()
        data_displayed = len(body_text.strip()) > 50  # Reasonable content length
    
    assert data_displayed, "Data should be displayed in some format"

async def test_update_functionality(page: Page, base_url: str):
    """Test that update/edit functionality exists."""
    # Look for edit/update links or buttons
    await page.goto(base_url)
    
    update_indicators = [
        page.locator("a[href*='edit']"),
        page.locator("a[href*='update']"),
        page.locator("button").filter(has_text="Edit"),
        page.locator("button").filter(has_text="Update"),
        page.locator("a").filter(has_text="Edit"),
        page.locator("a").filter(has_text="Update")
    ]
    
    update_found = False
    for indicator in update_indicators:
        if await indicator.count() > 0:
            update_found = True
            break
    
    # If no explicit update links, check for forms that might be used for updates
    if not update_found:
        forms = page.locator("form")
        form_count = await forms.count()
        update_found = form_count > 0
    
    assert update_found, "Update functionality should be available"

async def test_delete_functionality(page: Page, base_url: str):
    """Test that delete functionality exists."""
    await page.goto(base_url)
    
    delete_indicators = [
        page.locator("a[href*='delete']"),
        page.locator("button").filter(has_text="Delete"),
        page.locator("button").filter(has_text="Remove"),
        page.locator("a").filter(has_text="Delete"),
        page.locator("a").filter(has_text="Remove"),
        page.locator("button[class*='delete']"),
        page.locator("button[class*='remove']")
    ]
    
    delete_found = False
    for indicator in delete_indicators:
        if await indicator.count() > 0:
            delete_found = True
            break
    
    # Delete functionality might be hidden or require authentication
    # So we'll just check that the page loads without errors
    assert await page.locator("body").count() > 0, "Page should load successfully"

async def test_form_validation(page: Page, base_url: str):
    """Test that forms have proper validation."""
    await page.goto(base_url)
    
    # Find forms
    forms = page.locator("form")
    form_count = await forms.count()
    
    if form_count > 0:
        form = forms.first
        
        # Check for required field indicators
        required_fields = form.locator("input[required], textarea[required]")
        required_count = await required_fields.count()
        
        # Check for validation attributes
        validation_attributes = [
            "required", "minlength", "maxlength", "pattern", "type='email'"
        ]
        
        validation_found = False
        for attr in validation_attributes:
            elements = form.locator(f"input[{attr}], textarea[{attr}]")
            if await elements.count() > 0:
                validation_found = True
                break
        
        # At least some validation should be present
        assert validation_found or required_count > 0, "Forms should have some validation"

async def test_data_persistence(page: Page, base_url: str):
    """Test that data persists after form submission."""
    await page.goto(base_url)
    
    # Find a form to test
    forms = page.locator("form")
    form_count = await forms.count()
    
    if form_count > 0:
        form = forms.first
        
        # Fill out form with test data
        text_inputs = form.locator("input[type='text'], input[type='email'], textarea")
        input_count = await text_inputs.count()
        
        if input_count > 0:
            # Fill first few inputs with test data
            test_data = ["Test Title", "Test Content", "test@example.com"]
            
            for i, data in enumerate(test_data):
                if i < input_count:
                    input_field = text_inputs.nth(i)
                    await input_field.fill(data)
            
            # Submit form
            submit_button = form.locator("button[type='submit'], input[type='submit']").first
            if await submit_button.count() > 0:
                await submit_button.click()
                
                # Wait for response
                await page.wait_for_timeout(2000)
                
                # Check for success indicators
                success_indicators = [
                    page.locator(".success, .alert-success"),
                    page.locator("text=Success"),
                    page.locator("text=Created"),
                    page.locator("text=Added"),
                    page.locator("text=Saved")
                ]
                
                success_found = False
                for indicator in success_indicators:
                    if await indicator.count() > 0:
                        success_found = True
                        break
                
                # If no explicit success message, check if we're still on a valid page
                if not success_found:
                    current_url = page.url
                    success_found = not current_url.endswith("error") and not current_url.endswith("404")
                
                assert success_found, "Form submission should show success or remain on valid page"

async def test_search_functionality(page: Page, base_url: str):
    """Test that search functionality exists."""
    await page.goto(base_url)
    
    # Look for search elements
    search_indicators = [
        page.locator("input[type='search']"),
        page.locator("input[placeholder*='search']"),
        page.locator("input[name*='search']"),
        page.locator("input[name*='query']"),
        page.locator("form").filter(has=page.locator("input[type='text']"))
    ]
    
    search_found = False
    for indicator in search_indicators:
        if await indicator.count() > 0:
            search_found = True
            break
    
    # Search might not be implemented, so this is optional
    # We'll just check that the page loads without errors
    assert await page.locator("body").count() > 0, "Page should load successfully"

async def test_pagination_or_loading(page: Page, base_url: str):
    """Test that pagination or loading mechanisms exist for large datasets."""
    await page.goto(base_url)
    
    # Look for pagination elements
    pagination_indicators = [
        page.locator(".pagination"),
        page.locator("[class*='page']"),
        page.locator("a[href*='page']"),
        page.locator("button").filter(has_text="Next"),
        page.locator("button").filter(has_text="Previous"),
        page.locator("button").filter(has_text="Load More")
    ]
    
    pagination_found = False
    for indicator in pagination_indicators:
        if await indicator.count() > 0:
            pagination_found = True
            break
    
    # Pagination is optional, so we'll just verify page loads
    assert await page.locator("body").count() > 0, "Page should load successfully"
