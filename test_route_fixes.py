#!/usr/bin/env python3
"""
Test script to verify that the router fixes work correctly
"""

import sys
sys.path.append('app')

def test_article_service_import():
    """Test that the article service can be imported and instantiated"""
    try:
        from services.article import ArticleSettings, extract_article
        
        # Test that ArticleSettings can be created
        settings = ArticleSettings(
            cache=False,
            screenshot=True,
            full_content=True,
            sleep_ms=1000,
            wait_until="domcontentloaded",
            timeout_ms=60000,
            device="Desktop Chrome",
            user_scripts=[],
            user_scripts_timeout_ms=0,
            incognito=True,
            proxy=None,
            extra_http_headers={},
        )
        
        print("✅ ArticleSettings created successfully")
        print(f"   sleep_ms: {settings.sleep_ms}")
        print(f"   timeout_ms: {settings.timeout_ms}")
        print(f"   wait_until: {settings.wait_until}")
        
        return True
        
    except Exception as e:
        print(f"❌ Article service test failed: {e}")
        return False

def test_links_service_import():
    """Test that the links service can be imported and instantiated"""
    try:
        from services.links import LinkSettings, extract_links
        
        # Test that LinkSettings can be created
        settings = LinkSettings(
            cache=False,
            screenshot=False,
            full_content=False,
            sleep_ms=500,
            wait_until="domcontentloaded",
            timeout_ms=30000,
            device="Desktop Chrome",
            user_scripts=[],
            user_scripts_timeout_ms=0,
            incognito=True,
            proxy=None,
            extra_http_headers={},
            text_len_threshold=40,
            words_threshold=3,
        )
        
        print("✅ LinkSettings created successfully")
        print(f"   sleep_ms: {settings.sleep_ms}")
        print(f"   timeout_ms: {settings.timeout_ms}")
        print(f"   text_len_threshold: {settings.text_len_threshold}")
        
        return True
        
    except Exception as e:
        print(f"❌ Links service test failed: {e}")
        return False

def test_query_params_compatibility():
    """Test that query params can be created and mapped correctly"""
    try:
        from router.query_params import CommonQueryParams, BrowserQueryParams, ProxyQueryParams
        
        # Test CommonQueryParams
        common = CommonQueryParams(cache=True, screenshot=False, full_content=True)
        print("✅ CommonQueryParams created")
        print(f"   Has cache: {hasattr(common, 'cache')}")
        print(f"   Has user_scripts: {hasattr(common, 'user_scripts')}")
        print(f"   Has user_scripts_timeout: {hasattr(common, 'user_scripts_timeout')}")
        
        # Test BrowserQueryParams  
        browser = BrowserQueryParams(sleep=1000, timeout=60000, wait_until="domcontentloaded")
        print("✅ BrowserQueryParams created")
        print(f"   sleep: {browser.sleep}")
        print(f"   timeout: {browser.timeout}")
        print(f"   wait_until: {browser.wait_until}")
        
        # Test ProxyQueryParams
        proxy = ProxyQueryParams(proxy_server="http://proxy:8080")
        print("✅ ProxyQueryParams created")
        print(f"   proxy_server: {proxy.proxy_server}")
        
        return True
        
    except Exception as e:
        print(f"❌ Query params test failed: {e}")
        return False

def test_parameter_mapping():
    """Test the actual parameter mapping that was causing the error"""
    try:
        from router.query_params import CommonQueryParams, BrowserQueryParams, ProxyQueryParams
        from services.article import ArticleSettings
        
        # Simulate the router parameter creation
        params = CommonQueryParams(cache=False, screenshot=True, full_content=True)
        browser_params = BrowserQueryParams(sleep=1000, timeout=60000)
        proxy_params = ProxyQueryParams()
        
        # Test the mapping that was failing before
        settings = ArticleSettings(
            cache=params.cache,
            screenshot=params.screenshot,
            full_content=params.full_content,
            sleep_ms=browser_params.sleep,  # This was the fix
            wait_until=browser_params.wait_until,
            timeout_ms=browser_params.timeout,  # This was also fixed
            device=browser_params.device,
            user_scripts=params.user_scripts,
            user_scripts_timeout_ms=params.user_scripts_timeout,
            incognito=browser_params.incognito,
            proxy=proxy_params.proxy_server,  # This was fixed too
            extra_http_headers=proxy_params.extra_http_headers or {},
        )
        
        print("✅ Parameter mapping works correctly")
        print(f"   Mapped sleep_ms: {settings.sleep_ms}")
        print(f"   Mapped timeout_ms: {settings.timeout_ms}")
        print(f"   Mapped proxy: {settings.proxy}")
        
        return True
        
    except Exception as e:
        print(f"❌ Parameter mapping test failed: {e}")
        return False

def main():
    print("🧪 Testing Router Fixes")
    print("=======================")
    
    tests = [
        test_article_service_import,
        test_links_service_import,
        test_query_params_compatibility,
        test_parameter_mapping,
    ]
    
    passed = 0
    for test in tests:
        print(f"\n📋 Running {test.__name__}...")
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"💥 Unexpected error in {test.__name__}: {e}")
            print()
    
    total = len(tests)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Router fixes are working correctly.")
        print("The AttributeError should now be resolved.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())