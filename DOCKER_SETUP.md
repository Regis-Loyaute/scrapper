# Docker Setup Guide - Scrapper with Crawler Features

## Quick Start

### Option 1: Automated Setup (Recommended)
```bash
./setup_and_run.sh
```

### Option 2: Manual Docker Compose
```bash
# Create directories
mkdir -p user_data user_scripts

# Build and run
docker-compose up -d

# Check status
docker-compose ps
```

### Option 3: Manual Docker Build
```bash
# Build image
docker build -t scrapper:latest .

# Run container
docker run -d \
  --name scrapper \
  -p 3000:3000 \
  -v $(pwd)/user_data:/home/pwuser/user_data \
  -v $(pwd)/user_scripts:/home/pwuser/user_scripts \
  scrapper:latest
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Interface to bind |
| `PORT` | `3000` | Web server port |
| `LOG_LEVEL` | `info` | Logging level |
| `BROWSER_CONTEXT_LIMIT` | `20` | Max browser contexts |
| `CRAWL_MAX_CONCURRENCY` | `4` | Max crawler workers |
| `CRAWL_DEFAULT_RATE_PER_DOMAIN` | `1.0` | Requests per second per domain |
| `CRAWL_HARD_PAGE_LIMIT` | `1000` | Max pages per crawl job |
| `CRAWL_HARD_DURATION_SEC` | `3600` | Max crawl duration (1 hour) |
| `CRAWL_ENABLE_ASSET_CAPTURE` | `true` | Enable binary asset downloads |

### Volume Mounts

- `./user_data:/home/pwuser/user_data` - Application data and crawl results
- `./user_scripts:/home/pwuser/user_scripts` - Custom JavaScript scripts

## Usage

### Access the Application
- **Web Interface**: http://localhost:3000
- **API Documentation**: http://localhost:3000/docs
- **Health Check**: http://localhost:3000/ping

### API Examples

#### Extract Article Content
```bash
curl "http://localhost:3000/api/article?url=https://example.com&screenshot=true"
```

#### Extract Page Links
```bash
curl "http://localhost:3000/api/links?url=https://news.ycombinator.com"
```

#### Start Crawler (when REST API is completed)
```bash
curl -X POST "http://localhost:3000/api/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "scope": "domain",
    "max_depth": 2,
    "max_pages": 100,
    "screenshot": true
  }'
```

## Directory Structure

After running, your directory structure will be:

```
scrapper/
├── docker-compose.yml
├── .env
├── user_data/                 # Application data (mounted volume)
│   ├── _res/                 # Cache for single-page extractions
│   ├── crawls/               # Crawler job results
│   │   └── {job_id}/
│   │       ├── manifest.json  # Job metadata
│   │       ├── pages/         # Extracted page content
│   │       ├── blobs/         # Binary assets (if captured)
│   │       ├── logs.txt       # Crawl logs
│   │       └── exports/       # Generated exports (JSONL, ZIP)
│   └── _robots_cache/        # Robots.txt cache
└── user_scripts/             # Custom JavaScript scripts (mounted volume)
```

## Monitoring

### Check Container Status
```bash
docker-compose ps
```

### View Logs
```bash
# Follow all logs
docker-compose logs -f

# View specific service logs
docker logs scrapper

# View last 100 lines
docker logs --tail 100 scrapper
```

### Monitor Resource Usage
```bash
docker stats scrapper
```

## Security

### Authentication Setup
Create an htpasswd file to enable basic authentication:

```bash
# Install htpasswd (if not available)
sudo apt-get install apache2-utils  # Ubuntu/Debian
# or
brew install httpd  # macOS

# Create htpasswd file
htpasswd -c user_data/.htpasswd username

# Update .env file
echo "BASIC_HTPASSWD=/home/pwuser/user_data/.htpasswd" >> .env

# Restart container
docker-compose restart
```

### File Permissions
The container runs as UID 1001 for security. Ensure proper permissions:

```bash
sudo chown -R 1001:1001 user_data user_scripts
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs scrapper

# Check if port is already in use
netstat -tlnp | grep 3000
lsof -i :3000

# Try different port
docker-compose down
sed -i 's/3000:3000/3001:3000/' docker-compose.yml
docker-compose up -d
```

### Playwright Browser Issues
```bash
# Check if browser dependencies are available
docker exec scrapper playwright install-deps

# Restart container
docker-compose restart
```

### Permission Issues
```bash
# Fix volume permissions
sudo chown -R 1001:1001 user_data user_scripts

# Or run with current user
docker-compose down
docker-compose up -d --build
```

### Memory Issues
If the container uses too much memory:

```bash
# Reduce browser context limit
echo "BROWSER_CONTEXT_LIMIT=10" >> .env
echo "CRAWL_MAX_CONCURRENCY=2" >> .env
docker-compose restart
```

## Performance Tuning

### For High-Volume Usage
```bash
# Increase limits in .env
echo "BROWSER_CONTEXT_LIMIT=50" >> .env
echo "CRAWL_MAX_CONCURRENCY=8" >> .env
echo "CRAWL_HARD_PAGE_LIMIT=5000" >> .env

# Increase container resources in docker-compose.yml
mem_limit: 4g
cpus: 2.0
```

### For Light Usage
```bash
# Reduce resource usage
echo "BROWSER_CONTEXT_LIMIT=5" >> .env
echo "CRAWL_MAX_CONCURRENCY=2" >> .env

mem_limit: 1g
cpus: 0.5
```

## Backup and Restore

### Backup Crawl Data
```bash
tar -czf scrapper-backup-$(date +%Y%m%d).tar.gz user_data/
```

### Restore Data
```bash
tar -xzf scrapper-backup-YYYYMMDD.tar.gz
sudo chown -R 1001:1001 user_data/
docker-compose restart
```

## Updating

### Update to Latest Version
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Development

### Development Mode
```bash
# Enable debug mode
echo "DEBUG=true" >> .env
echo "LOG_LEVEL=debug" >> .env

# Mount source code for development
# Add to docker-compose.yml volumes:
# - ./app:/home/pwuser/app

docker-compose restart
```

### Running Tests
```bash
# Run the compatibility test
docker exec scrapper python3 test_crawler_compatibility.py

# Run the full Docker test suite
./docker_test_script.sh
```