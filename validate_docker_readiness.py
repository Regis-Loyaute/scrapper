#!/usr/bin/env python3
"""
Docker Readiness Validation Script

This script validates that all files and configurations are properly set up
for Docker deployment of the crawler feature.
"""

import os
import json
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists and is readable."""
    if Path(filepath).exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ Missing {description}: {filepath}")
        return False

def check_dockerfile():
    """Validate Dockerfile configuration."""
    print("🐳 Checking Dockerfile...")
    
    if not check_file_exists("Dockerfile", "Dockerfile"):
        return False
    
    with open("Dockerfile", "r") as f:
        content = f.read()
    
    checks = [
        ("playwright/python", "Uses Playwright base image"),
        ("USER_UID=1001", "Sets correct user UID"),
        ("USER $USER", "Switches to non-root user"),
        ("requirements.txt", "Installs dependencies"),
        ("HEALTHCHECK", "Includes health check"),
    ]
    
    all_passed = True
    for check, desc in checks:
        if check in content:
            print(f"  ✅ {desc}")
        else:
            print(f"  ❌ {desc}")
            all_passed = False
    
    return all_passed

def check_docker_compose():
    """Validate docker-compose.yml configuration."""
    print("📦 Checking docker-compose.yml...")
    
    if not check_file_exists("docker-compose.yml", "Docker Compose file"):
        return False
    
    try:
        import yaml
        with open("docker-compose.yml", "r") as f:
            compose = yaml.safe_load(f)
    except ImportError:
        print("  ⚠️  PyYAML not available, skipping detailed validation")
        return True
    except Exception as e:
        print(f"  ❌ Invalid YAML: {e}")
        return False
    
    # Check key configurations
    services = compose.get("services", {})
    scrapper = services.get("scrapper", {})
    
    checks = [
        (scrapper.get("ports"), "Port mapping configured"),
        (scrapper.get("volumes"), "Volume mounts configured"),
        (scrapper.get("environment"), "Environment variables set"),
        (scrapper.get("healthcheck"), "Health check configured"),
    ]
    
    all_passed = True
    for check, desc in checks:
        if check:
            print(f"  ✅ {desc}")
        else:
            print(f"  ❌ {desc}")
            all_passed = False
    
    return all_passed

def check_requirements():
    """Check requirements.txt has all needed dependencies."""
    print("📋 Checking requirements.txt...")
    
    if not check_file_exists("requirements.txt", "Requirements file"):
        return False
    
    with open("requirements.txt", "r") as f:
        requirements = f.read().lower()
    
    needed_deps = [
        "fastapi",
        "uvicorn",
        "playwright", 
        "pydantic",
        "httpx",
        "beautifulsoup4",
        "tldextract"
    ]
    
    all_passed = True
    for dep in needed_deps:
        if dep in requirements:
            print(f"  ✅ {dep}")
        else:
            print(f"  ❌ Missing: {dep}")
            all_passed = False
    
    return all_passed

def check_app_structure():
    """Validate application structure."""
    print("📁 Checking application structure...")
    
    required_files = [
        ("app/main.py", "Main application"),
        ("app/settings.py", "Settings module"),
        ("app/crawler/models.py", "Crawler models"),
        ("app/crawler/normalizer.py", "URL normalizer"),
        ("app/crawler/scope.py", "Scope checker"),
        ("app/crawler/robots.py", "Robots handler"),
        ("app/crawler/frontier.py", "URL frontier"),
        ("app/crawler/ratelimit.py", "Rate limiter"),
        ("app/crawler/storage.py", "Storage system"),
        ("app/crawler/extract.py", "Extract helpers"),
        ("app/crawler/crawler.py", "Main crawler"),
        ("app/services/article.py", "Article service"),
        ("app/services/links.py", "Links service"),
    ]
    
    all_passed = True
    for filepath, desc in required_files:
        if not check_file_exists(filepath, desc):
            all_passed = False
    
    return all_passed

def check_setup_scripts():
    """Check setup and test scripts."""
    print("🔧 Checking setup scripts...")
    
    scripts = [
        ("setup_and_run.sh", "Setup script"),
        ("test_docker_setup.sh", "Test script"),
        ("docker_test_script.sh", "Docker validation script"),
        (".env", "Environment file"),
    ]
    
    all_passed = True
    for script, desc in scripts:
        if not check_file_exists(script, desc):
            all_passed = False
        elif script.endswith('.sh'):
            # Check if executable
            if os.access(script, os.X_OK):
                print(f"  ✅ {desc} is executable")
            else:
                print(f"  ⚠️  {desc} not executable (chmod +x {script})")
    
    return all_passed

def check_directories():
    """Check required directories exist."""
    print("📂 Checking directories...")
    
    required_dirs = [
        "app",
        "app/crawler", 
        "app/services",
        "app/router",
        "app/internal",
    ]
    
    all_passed = True
    for directory in required_dirs:
        if Path(directory).is_dir():
            print(f"  ✅ {directory}/")
        else:
            print(f"  ❌ Missing directory: {directory}/")
            all_passed = False
    
    # Create user_data and user_scripts if they don't exist
    for user_dir in ["user_data", "user_scripts"]:
        if not Path(user_dir).exists():
            Path(user_dir).mkdir()
            print(f"  ✅ Created {user_dir}/")
        else:
            print(f"  ✅ {user_dir}/ exists")
    
    return all_passed

def main():
    """Run all validation checks."""
    print("🚀 Docker Readiness Validation")
    print("===============================")
    print()
    
    checks = [
        check_dockerfile,
        check_docker_compose,
        check_requirements,
        check_app_structure,
        check_setup_scripts,
        check_directories,
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
            print()
        except Exception as e:
            print(f"  💥 Error in check: {e}")
            results.append(False)
            print()
    
    passed = sum(results)
    total = len(results)
    
    print("📊 Validation Summary")
    print("====================")
    print(f"Passed: {passed}/{total} checks")
    print()
    
    if passed == total:
        print("🎉 All checks passed! Ready for Docker deployment.")
        print()
        print("🚀 To build and run:")
        print("   ./setup_and_run.sh")
        print("   # OR")
        print("   docker-compose up -d")
        print()
        print("🧪 To test after running:")
        print("   ./test_docker_setup.sh")
        return 0
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print()
        print("💡 Common fixes:")
        print("   chmod +x *.sh              # Make scripts executable")
        print("   mkdir -p user_data user_scripts  # Create directories")
        print("   pip install -r requirements.txt  # Install dependencies")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())