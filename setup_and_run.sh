#!/bin/bash

# Setup and run script for Scrapper with Crawler features
# This script builds the Docker image and starts the application

set -e

echo "🚀 Setting up Scrapper with Crawler Features"
echo "=============================================="

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    echo "Please install Docker and try again"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available"
    echo "Please install Docker Compose and try again"
    exit 1
fi

# Create required directories
echo "📁 Creating required directories..."
mkdir -p user_data user_scripts
chmod 755 user_data user_scripts

# Set proper ownership for container (UID 1001)
echo "🔒 Setting up permissions..."
if command -v chown &> /dev/null; then
    sudo chown -R 1001:1001 user_data user_scripts 2>/dev/null || echo "⚠️  Could not set ownership - permissions may need adjustment"
fi

# Build and start the application
echo "🐳 Building Docker image..."
if command -v docker-compose &> /dev/null; then
    docker-compose build
    echo "🌟 Starting Scrapper..."
    docker-compose up -d
elif docker compose version &> /dev/null; then
    docker compose build
    echo "🌟 Starting Scrapper..."
    docker compose up -d
else
    echo "❌ Docker Compose command not found"
    exit 1
fi

# Wait for application to start
echo "⏳ Waiting for application to start..."
sleep 10

# Check if container is running
if docker ps | grep -q scrapper; then
    echo "✅ Scrapper is running successfully!"
    echo ""
    echo "🌐 Access the application:"
    echo "   Web Interface: http://localhost:3000"
    echo "   API Documentation: http://localhost:3000/docs"
    echo ""
    echo "📋 Available API endpoints:"
    echo "   GET  /ping                     - Health check"
    echo "   GET  /api/article?url=...      - Extract article content"
    echo "   GET  /api/links?url=...        - Extract page links"
    echo "   POST /api/crawl                - Start crawl job (when REST API is completed)"
    echo ""
    echo "📊 Monitor the application:"
    echo "   docker logs scrapper           - View application logs"
    echo "   docker-compose logs -f         - Follow logs"
    echo "   docker-compose ps              - Check status"
    echo ""
    echo "🛑 Stop the application:"
    echo "   docker-compose down            - Stop and remove containers"
    echo "   docker-compose down -v         - Stop and remove data volumes"
else
    echo "❌ Container failed to start properly"
    echo "📋 Checking logs..."
    docker logs scrapper || echo "No logs available"
    exit 1
fi

# Test basic functionality
echo "🧪 Testing basic functionality..."

# Test health check
if curl -f http://localhost:3000/ping > /dev/null 2>&1; then
    echo "✅ Health check passed"
else
    echo "⚠️  Health check failed - application may still be starting"
fi

# Test API endpoints (expect 422 without parameters)
echo "🔍 Testing API endpoints..."
ARTICLE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/article 2>/dev/null)
LINKS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/links 2>/dev/null)

if [[ "$ARTICLE_STATUS" == "422" ]]; then
    echo "✅ Article API endpoint accessible"
else
    echo "⚠️  Article API returned status: $ARTICLE_STATUS"
fi

if [[ "$LINKS_STATUS" == "422" ]]; then
    echo "✅ Links API endpoint accessible"
else
    echo "⚠️  Links API returned status: $LINKS_STATUS"
fi

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "💡 Next steps:"
echo "   1. Visit http://localhost:3000 to see the web interface"
echo "   2. Try the API: curl 'http://localhost:3000/api/article?url=https://example.com'"
echo "   3. Check the user_data/ directory for crawl results (when using crawler)"
echo ""
echo "📚 For more information, see the documentation in docs/ directory"