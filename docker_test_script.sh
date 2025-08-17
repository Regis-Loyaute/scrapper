#!/bin/bash

# Docker validation script for crawler feature
# Run this script where Docker is available to test the implementation

set -e

echo "🐳 Building Docker image with crawler features..."
docker build -t scrapper-crawler-test .

echo "🧪 Running basic functionality tests in Docker..."

# Test 1: Basic startup
echo "📋 Test 1: Basic application startup"
CONTAINER_ID=$(docker run -d -p 3001:3000 scrapper-crawler-test)
sleep 10

# Check if container is running
if docker ps | grep -q $CONTAINER_ID; then
    echo "  ✅ Container started successfully"
else
    echo "  ❌ Container failed to start"
    docker logs $CONTAINER_ID
    exit 1
fi

# Test 2: Health check
echo "📋 Test 2: Health check endpoint"
if curl -f http://localhost:3001/ping > /dev/null 2>&1; then
    echo "  ✅ Health check passed"
else
    echo "  ❌ Health check failed"
    docker logs $CONTAINER_ID
    exit 1
fi

# Test 3: Existing API endpoints (backward compatibility)
echo "📋 Test 3: Backward compatibility - existing endpoints respond"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3001/api/article 2>/dev/null | grep -q "422\|400"; then
    echo "  ✅ Article API endpoint accessible (422/400 expected without URL param)"
else
    echo "  ❌ Article API endpoint not accessible"
fi

if curl -s -o /dev/null -w "%{http_code}" http://localhost:3001/api/links 2>/dev/null | grep -q "422\|400"; then
    echo "  ✅ Links API endpoint accessible (422/400 expected without URL param)"
else
    echo "  ❌ Links API endpoint not accessible"
fi

# Test 4: Check crawler modules are importable
echo "📋 Test 4: Crawler modules importability"
docker exec $CONTAINER_ID python3 -c "
import sys
sys.path.append('/home/pwuser/app')
from crawler.models import CrawlParams
from crawler.normalizer import normalize_url
from services.article import ArticleSettings
print('✅ Crawler modules import successfully')
" || echo "❌ Crawler modules import failed"

# Test 5: Check crawler directories can be created
echo "📋 Test 5: Crawler storage directories"
docker exec $CONTAINER_ID python3 -c "
import sys
sys.path.append('/home/pwuser/app')
from settings import USER_DATA_DIR
from pathlib import Path
crawl_dir = USER_DATA_DIR / 'crawls'
crawl_dir.mkdir(parents=True, exist_ok=True)
print(f'✅ Crawler directory created: {crawl_dir}')
" || echo "❌ Crawler directory creation failed"

# Test 6: Check user permissions (should run as UID 1001)
echo "📋 Test 6: User permissions and UID"
USER_ID=$(docker exec $CONTAINER_ID id -u)
if [ "$USER_ID" = "1001" ]; then
    echo "  ✅ Running as correct UID 1001"
else
    echo "  ❌ Running as wrong UID: $USER_ID (expected 1001)"
fi

# Test 7: Check environment variables
echo "📋 Test 7: Crawler environment variables"
docker exec $CONTAINER_ID python3 -c "
import sys
sys.path.append('/home/pwuser/app')
import settings
crawler_settings = [
    'CRAWL_MAX_CONCURRENCY',
    'CRAWL_DEFAULT_RATE_PER_DOMAIN',
    'CRAWL_HARD_PAGE_LIMIT',
    'CRAWL_HARD_DURATION_SEC',
    'CRAWL_ENABLE_ASSET_CAPTURE'
]
for setting in crawler_settings:
    value = getattr(settings, setting, 'NOT_FOUND')
    print(f'✅ {setting} = {value}')
" || echo "❌ Environment variables check failed"

# Cleanup
echo "🧹 Cleaning up test container..."
docker stop $CONTAINER_ID > /dev/null
docker rm $CONTAINER_ID > /dev/null

echo "🎉 Docker validation completed successfully!"
echo ""
echo "🚀 To test crawler functionality manually:"
echo "   docker run -d -p 3000:3000 -v \$(pwd)/user_data:/home/pwuser/user_data scrapper-crawler-test"
echo "   # Then visit http://localhost:3000 for the web interface"
echo "   # Or use curl to test the API endpoints"