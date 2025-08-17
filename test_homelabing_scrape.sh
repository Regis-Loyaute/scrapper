#!/bin/bash

# Test script to validate scraping functionality with homelabing.com
# Run this script to test the application after fixing the AttributeErrors

set -e

echo "🧪 Testing Scrapper with homelabing.com"
echo "========================================"

# Configuration
BASE_URL="http://localhost:3000"
TEST_URL="https://homelabing.com"
OUTPUT_DIR="./test_results"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Function to test an endpoint
test_endpoint() {
    local endpoint="$1"
    local description="$2"
    local output_file="$3"
    
    echo "📋 Testing $description..."
    echo "   URL: $BASE_URL$endpoint"
    
    # Make the request and capture response
    if curl -s -w "\nHTTP_STATUS:%{http_code}\nTIME_TOTAL:%{time_total}\n" \
        "$BASE_URL$endpoint" > "$output_file" 2>&1; then
        
        # Extract HTTP status and timing
        HTTP_STATUS=$(tail -2 "$output_file" | grep "HTTP_STATUS:" | cut -d: -f2)
        TIME_TOTAL=$(tail -1 "$output_file" | grep "TIME_TOTAL:" | cut -d: -f2)
        
        # Remove status lines from output
        head -n -2 "$output_file" > "${output_file}.tmp" && mv "${output_file}.tmp" "$output_file"
        
        if [ "$HTTP_STATUS" = "200" ]; then
            echo "   ✅ Success (${TIME_TOTAL}s)"
            
            # Check if response contains expected fields
            if grep -q '"title"' "$output_file" 2>/dev/null; then
                TITLE=$(grep -o '"title":"[^"]*"' "$output_file" | head -1 | cut -d'"' -f4)
                echo "   📄 Found title: $TITLE"
            fi
            
            if grep -q '"url"' "$output_file" 2>/dev/null; then
                echo "   🔗 URL field present"
            fi
            
            if grep -q '"content"' "$output_file" 2>/dev/null; then
                CONTENT_LENGTH=$(grep -o '"content":"[^"]*"' "$output_file" | head -1 | cut -d'"' -f4 | wc -c)
                echo "   📝 Content length: ${CONTENT_LENGTH} characters"
            fi
            
            if grep -q '"links"' "$output_file" 2>/dev/null; then
                LINKS_COUNT=$(grep -o '"url":"[^"]*"' "$output_file" | wc -l)
                echo "   🔗 Links found: $LINKS_COUNT"
            fi
            
        elif [ "$HTTP_STATUS" = "422" ]; then
            echo "   ⚠️  Validation error (422) - check parameters"
            echo "   Response: $(head -1 "$output_file")"
        else
            echo "   ❌ HTTP $HTTP_STATUS (${TIME_TOTAL}s)"
            echo "   Response: $(head -3 "$output_file")"
        fi
    else
        echo "   ❌ Request failed"
        cat "$output_file"
    fi
    echo
}

# Check if application is running
echo "🔍 Checking if application is running..."
if curl -f "$BASE_URL/ping" > /dev/null 2>&1; then
    echo "✅ Application is running"
else
    echo "❌ Application is not responding at $BASE_URL"
    echo "💡 Make sure to run: docker-compose up -d"
    exit 1
fi
echo

# Test 1: Basic article extraction
test_endpoint "/api/article?url=${TEST_URL}" \
    "Article extraction from homelabing.com" \
    "$OUTPUT_DIR/article_basic.json"

# Test 2: Article with screenshot
test_endpoint "/api/article?url=${TEST_URL}&screenshot=true" \
    "Article with screenshot" \
    "$OUTPUT_DIR/article_screenshot.json"

# Test 3: Article with full content
test_endpoint "/api/article?url=${TEST_URL}&full-content=true" \
    "Article with full content" \
    "$OUTPUT_DIR/article_full.json"

# Test 4: Article with all options
test_endpoint "/api/article?url=${TEST_URL}&screenshot=true&full-content=true&cache=false" \
    "Article with all options" \
    "$OUTPUT_DIR/article_all_options.json"

# Test 5: Links extraction
test_endpoint "/api/links?url=${TEST_URL}" \
    "Links extraction from homelabing.com" \
    "$OUTPUT_DIR/links_basic.json"

# Test 6: Links with custom thresholds
test_endpoint "/api/links?url=${TEST_URL}&text-len-threshold=20&words-threshold=2" \
    "Links with custom thresholds" \
    "$OUTPUT_DIR/links_custom.json"

# Test 7: Test with browser parameters
test_endpoint "/api/article?url=${TEST_URL}&device=Desktop+Chrome&timeout=30000&sleep=1000" \
    "Article with browser parameters" \
    "$OUTPUT_DIR/article_browser_params.json"

# Test 8: Test error handling with invalid URL
test_endpoint "/api/article?url=invalid-url" \
    "Error handling with invalid URL" \
    "$OUTPUT_DIR/error_invalid_url.json"

# Summary
echo "📊 Test Summary"
echo "==============="
echo "Test results saved in: $OUTPUT_DIR/"
echo

if [ -f "$OUTPUT_DIR/article_basic.json" ]; then
    echo "🔍 Quick Analysis:"
    
    # Check for successful article extraction
    if grep -q '"title"' "$OUTPUT_DIR/article_basic.json" 2>/dev/null; then
        echo "✅ Article extraction working"
    else
        echo "⚠️  Article extraction may have issues"
    fi
    
    # Check for successful links extraction
    if [ -f "$OUTPUT_DIR/links_basic.json" ] && grep -q '"links"' "$OUTPUT_DIR/links_basic.json" 2>/dev/null; then
        echo "✅ Links extraction working"
    else
        echo "⚠️  Links extraction may have issues"
    fi
    
    # Check file sizes
    echo "📁 File sizes:"
    ls -lh "$OUTPUT_DIR"/*.json | awk '{print "   " $9 ": " $5}'
fi

echo
echo "💡 Next steps:"
echo "   1. Review the JSON files in $OUTPUT_DIR/"
echo "   2. Check for any error messages or empty responses"
echo "   3. Verify that titles and content were extracted correctly"
echo "   4. If successful, try with other websites"
echo
echo "🐳 Container logs: docker-compose logs -f"
echo "🌐 Web interface: $BASE_URL"