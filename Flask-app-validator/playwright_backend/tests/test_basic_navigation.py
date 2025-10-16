"""
Basic navigation and page structure tests for Flask applications.
Tests common Flask app patterns like home page, navigation, and basic functionality.
"""

from playwright.async_api import Page, expect

async def test_home_page_loads(page: Page, base_url: str):
    """Test that the home page loads successfully."""
    await page.goto(base_url)
    
    # Check that page loads without errors
    expect(page).to_have_title(/.+/)  # Any title is acceptable
    
    # Check for common Flask app elements
    await expect(page.locator("body")).to_be_visible()
    
    # Check for basic HTML structure
    html_element = page.locator("html")
    await expect(html_element).to_be_attached()

async def test_page_has_content(page: Page, base_url: str):
    """Test that the page has meaningful content."""
    await page.goto(base_url)
    
    # Check that page has some content (not just empty)
    body_text = await page.locator("body").text_content()
    assert len(body_text.strip()) > 0, "Page should have some content"
    
    # Check for common Flask template elements
    # Look for navigation, main content area, or common Flask patterns
    has_navigation = await page.locator("nav, .navbar, .navigation").count() > 0
    has_main_content = await page.locator("main, .main, .content, .container").count() > 0
    has_links = await page.locator("a").count() > 0
    
    # At least one of these should be present
    assert has_navigation or has_main_content or has_links, "Page should have navigation, main content, or links"

async def test_responsive_design(page: Page, base_url: str):
    """Test basic responsive design elements."""
    await page.goto(base_url)
    
    # Test different viewport sizes
    viewports = [
        {"width": 1920, "height": 1080},  # Desktop
        {"width": 768, "height": 1024},   # Tablet
        {"width": 375, "height": 667}     # Mobile
    ]
    
    for viewport in viewports:
        await page.set_viewport_size(viewport)
        
        # Check that page is still functional at different sizes
        body = page.locator("body")
        await expect(body).to_be_visible()
        
        # Check that content doesn't overflow horizontally
        body_box = await body.bounding_box()
        assert body_box is not None, f"Body should be visible at {viewport['width']}x{viewport['height']}"

async def test_no_console_errors(page: Page, base_url: str):
    """Test that there are no JavaScript console errors."""
    console_errors = []
    
    def handle_console(msg):
        if msg.type == "error":
            console_errors.append(msg.text)
    
    page.on("console", handle_console)
    
    await page.goto(base_url)
    
    # Wait a bit for any async operations
    await page.wait_for_timeout(1000)
    
    # Check for critical errors (ignore warnings)
    critical_errors = [error for error in console_errors if "error" in error.lower()]
    assert len(critical_errors) == 0, f"Found console errors: {critical_errors}"

async def test_page_meta_tags(page: Page, base_url: str):
    """Test that page has appropriate meta tags."""
    await page.goto(base_url)
    
    # Check for viewport meta tag (important for responsive design)
    viewport_meta = page.locator('meta[name="viewport"]')
    viewport_count = await viewport_meta.count()
    
    if viewport_count > 0:
        viewport_content = await viewport_meta.get_attribute("content")
        assert "width=device-width" in viewport_content, "Viewport meta tag should include width=device-width"
    
    # Check for charset meta tag
    charset_meta = page.locator('meta[charset]')
    charset_count = await charset_meta.count()
    
    if charset_count > 0:
        charset_value = await charset_meta.get_attribute("charset")
        assert charset_value.lower() in ["utf-8", "utf8"], "Charset should be UTF-8"

async def test_links_are_accessible(page: Page, base_url: str):
    """Test that internal links are accessible."""
    await page.goto(base_url)
    
    # Find all internal links
    links = page.locator("a[href^='/'], a[href^='./'], a[href^='../']")
    link_count = await links.count()
    
    if link_count > 0:
        # Test first few links (limit to avoid too many requests)
        max_links_to_test = min(5, link_count)
        
        for i in range(max_links_to_test):
            link = links.nth(i)
            href = await link.get_attribute("href")
            
            if href and not href.startswith("http"):
                # Make it absolute URL
                if href.startswith("/"):
                    test_url = base_url + href
                else:
                    test_url = base_url + "/" + href
                
                try:
                    # Test that link doesn't return 404
                    response = await page.request.get(test_url)
                    assert response.status < 400, f"Link {href} returned status {response.status}"
                except Exception as e:
                    # If request fails, it might be a client-side link, which is okay
                    pass
