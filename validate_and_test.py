#!/usr/bin/env python3
"""
Validation and testing guide for the scrapper application
"""

import json
import subprocess
import sys
from pathlib import Path

def check_container_status():
    """Check if Docker container is running"""
    try:
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if 'scrapper' in result.stdout:
            print("✅ Docker container is running")
            return True
        else:
            print("❌ Docker container is not running")
            print("💡 Run: docker-compose up -d")
            return False
    except FileNotFoundError:
        print("❌ Docker not found")
        return False

def check_application_health():
    """Check if application responds to health check"""
    try:
        result = subprocess.run(['curl', '-f', 'http://localhost:3000/ping'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Application health check passed")
            return True
        else:
            print("❌ Application health check failed")
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("❌ Cannot reach application (curl not available or timeout)")
        return False

def test_simple_extraction():
    """Test basic article extraction"""
    print("\n🧪 Testing basic extraction...")
    
    test_url = "https://homelabing.com"
    api_url = f"http://localhost:3000/api/article?url={test_url}"
    
    try:
        result = subprocess.run(['curl', '-s', api_url], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                
                if 'title' in response:
                    print(f"✅ Article extracted successfully")
                    print(f"   Title: {response.get('title', 'N/A')[:60]}...")
                    print(f"   Domain: {response.get('domain', 'N/A')}")
                    print(f"   Length: {response.get('length', 'N/A')} characters")
                    
                    if 'content' in response and response['content']:
                        print("✅ Content extracted")
                    else:
                        print("⚠️  No content extracted")
                    
                    return True
                else:
                    print("⚠️  Response missing title field")
                    print(f"   Response keys: {list(response.keys())}")
                    return False
                    
            except json.JSONDecodeError:
                print("❌ Invalid JSON response")
                print(f"   Response: {result.stdout[:200]}...")
                return False
        else:
            print("❌ Request failed")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Request timed out")
        return False
    except FileNotFoundError:
        print("❌ curl not available")
        return False

def suggest_tests():
    """Suggest comprehensive tests to run"""
    print("\n📋 Suggested Tests to Run:")
    print("=" * 40)
    
    print("\n1. 🔧 Automated Test Suite:")
    print("   ./test_homelabing_scrape.sh")
    
    print("\n2. 🎯 Quick Manual Tests:")
    print("   # Basic article")
    print('   curl "http://localhost:3000/api/article?url=https://homelabing.com"')
    
    print("\n   # With screenshot")
    print('   curl "http://localhost:3000/api/article?url=https://homelabing.com&screenshot=true"')
    
    print("\n   # Links extraction")
    print('   curl "http://localhost:3000/api/links?url=https://homelabing.com"')
    
    print("\n3. 🌐 Web Interface:")
    print("   Open http://localhost:3000 in your browser")
    
    print("\n4. 📊 Check Results:")
    print("   # Look for extracted content")
    print("   # Verify no AttributeError in logs")
    print("   # Check response times")
    
    print("\n5. 🔍 Monitor Logs:")
    print("   docker-compose logs -f scrapper")

def check_test_files():
    """Check if test files are available"""
    print("\n📁 Available Test Resources:")
    
    test_files = [
        ("./test_homelabing_scrape.sh", "Comprehensive test suite"),
        ("./manual_test_commands.md", "Manual testing guide"),
        ("./test_docker_setup.sh", "Docker validation"),
        ("./BUGFIX_SUMMARY.md", "Bug fix documentation"),
    ]
    
    for filepath, description in test_files:
        if Path(filepath).exists():
            print(f"✅ {filepath} - {description}")
        else:
            print(f"❌ {filepath} - {description}")

def main():
    """Main validation and testing workflow"""
    print("🚀 Scrapper Application Validation & Testing")
    print("=" * 50)
    
    # Check prerequisites
    container_ok = check_container_status()
    if not container_ok:
        print("\n❌ Container not running. Please start the application first.")
        return 1
    
    health_ok = check_application_health()
    if not health_ok:
        print("\n❌ Application not responding. Check logs with: docker-compose logs scrapper")
        return 1
    
    # Test basic functionality
    extraction_ok = test_simple_extraction()
    
    # Show test resources
    check_test_files()
    
    # Provide guidance
    suggest_tests()
    
    print("\n" + "=" * 50)
    if extraction_ok:
        print("🎉 Basic validation PASSED! Ready for comprehensive testing.")
        print("\n💡 Next steps:")
        print("   1. Run ./test_homelabing_scrape.sh for full test suite")
        print("   2. Try different websites and parameters")
        print("   3. Test the web interface at http://localhost:3000")
        return 0
    else:
        print("⚠️  Basic validation had issues. Check the problems above.")
        print("\n💡 Troubleshooting:")
        print("   1. Check container logs: docker-compose logs scrapper")
        print("   2. Restart container: docker-compose restart")
        print("   3. Verify URL is accessible: curl -I https://homelabing.com")
        return 1

if __name__ == "__main__":
    sys.exit(main())