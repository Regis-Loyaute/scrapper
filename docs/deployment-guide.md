# Deployment and Configuration Guide

This guide covers deployment strategies, configuration options, and operational considerations for running Scrapper with crawler functionality in various environments.

## Quick Deployment Options

### Option 1: Docker Run (Simple)

For basic single-page scraping:
```bash
docker run -d -p 3000:3000 --name scrapper amerkurev/scrapper:latest
```

For crawling with data persistence:
```bash
docker run -d \
  -p 3000:3000 \
  -v $(pwd)/user_data:/home/pwuser/user_data \
  -v $(pwd)/user_scripts:/home/pwuser/user_scripts \
  --name scrapper \
  amerkurev/scrapper:latest
```

### Option 2: Docker Compose (Recommended)

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  scrapper:
    image: amerkurev/scrapper:latest
    container_name: scrapper
    ports:
      - "3000:3000"
    volumes:
      - ./user_data:/home/pwuser/user_data
      - ./user_scripts:/home/pwuser/user_scripts
    environment:
      - LOG_LEVEL=info
      - CRAWL_MAX_CONCURRENCY=4
      - CRAWL_DEFAULT_RATE_PER_DOMAIN=1.0
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:3000/ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    mem_limit: 2g
    cpus: 1.0
```

Deploy:
```bash
docker-compose up -d
```

### Option 3: Production Deployment

For production environments with advanced configuration:
```yaml
version: '3.8'

services:
  scrapper:
    image: amerkurev/scrapper:latest
    container_name: scrapper
    ports:
      - "3000:3000"
    volumes:
      - /data/scrapper:/home/pwuser/user_data
      - ./user_scripts:/home/pwuser/user_scripts
      - ./ssl:/ssl:ro
      - ./.htpasswd:/.htpasswd:ro
    environment:
      # Security
      - BASIC_HTPASSWD=/.htpasswd
      - SSL_CERTFILE=/ssl/cert.pem
      - SSL_KEYFILE=/ssl/key.pem
      
      # Performance
      - UVICORN_WORKERS=4
      - CRAWL_MAX_CONCURRENCY=8
      - BROWSER_CONTEXT_LIMIT=30
      
      # Crawler settings
      - CRAWL_DEFAULT_RATE_PER_DOMAIN=2.0
      - CRAWL_HARD_PAGE_LIMIT=10000
      - CRAWL_HARD_DURATION_SEC=14400
      
      # Logging
      - LOG_LEVEL=warning
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:3000/ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    mem_limit: 4g
    cpus: 2.0
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
```

## Configuration Options

### Environment Variables

#### General Settings
| Variable | Description | Default | Recommended |
|----------|-------------|---------|-------------|
| `HOST` | Server bind address | 0.0.0.0 | 0.0.0.0 |
| `PORT` | Server port | 3000 | 3000 |
| `LOG_LEVEL` | Logging level | info | info/warning |
| `DEBUG` | Debug mode | false | false |
| `UVICORN_WORKERS` | Worker processes | 2 | 2-4 |

#### Browser Settings
| Variable | Description | Default | Recommended |
|----------|-------------|---------|-------------|
| `BROWSER_TYPE` | Browser engine | chromium | chromium |
| `BROWSER_CONTEXT_LIMIT` | Max browser tabs | 20 | 20-50 |
| `SCREENSHOT_TYPE` | Screenshot format | jpeg | jpeg |
| `SCREENSHOT_QUALITY` | JPEG quality | 80 | 80 |

#### Crawler Settings
| Variable | Description | Default | Recommended |
|----------|-------------|---------|-------------|
| `CRAWL_MAX_CONCURRENCY` | Parallel requests | 4 | 4-8 |
| `CRAWL_DEFAULT_RATE_PER_DOMAIN` | Requests/second | 1.0 | 1.0-2.0 |
| `CRAWL_HARD_PAGE_LIMIT` | Max pages per job | 1000 | 1000-10000 |
| `CRAWL_HARD_DURATION_SEC` | Max job duration | 3600 | 3600-14400 |
| `CRAWL_ENABLE_ASSET_CAPTURE` | Download assets | true | false |

### Volume Configuration

#### Required Volumes
```bash
# Data persistence (required for crawling)
-v /host/path/user_data:/home/pwuser/user_data

# Custom JavaScript (optional)
-v /host/path/user_scripts:/home/pwuser/user_scripts
```

#### Data Directory Structure
```
user_data/
├── _res/                    # Single-page cache
│   └── {hash}/
├── crawls/                  # Crawler data
│   ├── .job_registry.json   # Job registry
│   └── {domain}/            # Domain-based organization
│       └── {timestamp}_{jobid}/
│           ├── manifest.json
│           ├── logs.txt
│           ├── pages/
│           ├── blobs/
│           └── exports/
└── _robots_cache/           # Robots.txt cache
```

### Security Configuration

#### Basic Authentication
```bash
# Create password file
htpasswd -cbB .htpasswd admin your_secure_password

# Mount in container
-v $(pwd)/.htpasswd:/.htpasswd:ro
-e BASIC_HTPASSWD=/.htpasswd
```

#### HTTPS/SSL Setup
```bash
# Generate self-signed certificate (development)
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout key.pem -out cert.pem -days 365 \
  -subj '/CN=localhost'

# Mount certificates
-v $(pwd)/ssl:/ssl:ro
-e SSL_CERTFILE=/ssl/cert.pem
-e SSL_KEYFILE=/ssl/key.pem
```

#### Firewall Configuration
```bash
# Allow Scrapper port
ufw allow 3000/tcp

# Restrict to specific IPs (recommended)
ufw allow from 192.168.1.0/24 to any port 3000
```

## Performance Tuning

### Resource Allocation

#### Memory Requirements
- **Minimum**: 1GB RAM
- **Recommended**: 2-4GB RAM
- **Heavy crawling**: 4-8GB RAM

#### CPU Requirements
- **Minimum**: 1 CPU core
- **Recommended**: 2-4 CPU cores
- **Heavy crawling**: 4-8 CPU cores

#### Disk Space
- **Base installation**: ~2GB
- **Per crawl job**: 10-100MB (varies by site)
- **Recommended**: 50GB+ for production

### Docker Resource Limits
```yaml
services:
  scrapper:
    # ... other config
    mem_limit: 4g
    cpus: 2.0
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
```

### Crawler Performance Tuning

#### Concurrency Settings
```yaml
environment:
  # Light load (1-2 requests/sec total)
  - CRAWL_MAX_CONCURRENCY=2
  - CRAWL_DEFAULT_RATE_PER_DOMAIN=1.0
  
  # Medium load (4-8 requests/sec total)
  - CRAWL_MAX_CONCURRENCY=4
  - CRAWL_DEFAULT_RATE_PER_DOMAIN=2.0
  
  # Heavy load (8-16 requests/sec total)
  - CRAWL_MAX_CONCURRENCY=8
  - CRAWL_DEFAULT_RATE_PER_DOMAIN=2.0
```

#### Memory Optimization
```yaml
environment:
  # Reduce browser contexts for memory savings
  - BROWSER_CONTEXT_LIMIT=10
  
  # Disable asset capture to save bandwidth/storage
  - CRAWL_ENABLE_ASSET_CAPTURE=false
  
  # Use JPEG screenshots for smaller files
  - SCREENSHOT_TYPE=jpeg
  - SCREENSHOT_QUALITY=70
```

## Production Deployment

### Reverse Proxy Setup (Nginx)

```nginx
server {
    listen 80;
    server_name scrapper.example.com;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for real-time updates
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts for long-running operations
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### Load Balancer Setup

For high-availability deployments:

```yaml
version: '3.8'

services:
  scrapper-1:
    image: amerkurev/scrapper:latest
    environment:
      - UVICORN_WORKERS=2
    volumes:
      - /shared/data:/home/pwuser/user_data
    
  scrapper-2:
    image: amerkurev/scrapper:latest
    environment:
      - UVICORN_WORKERS=2
    volumes:
      - /shared/data:/home/pwuser/user_data
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - scrapper-1
      - scrapper-2
```

### Monitoring and Logging

#### Health Checks
```bash
# Basic health check
curl http://localhost:3000/ping

# Detailed health monitoring
curl http://localhost:3000/ping | jq
```

#### Log Management
```yaml
services:
  scrapper:
    # ... other config
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
```

#### Metrics Collection
```yaml
services:
  scrapper:
    # ... other config
    environment:
      - LOG_LEVEL=info
    labels:
      - "prometheus.io/scrape=true"
      - "prometheus.io/port=3000"
```

## Backup and Recovery

### Data Backup Strategy

#### Manual Backup
```bash
# Backup crawled data
tar -czf scrapper-backup-$(date +%Y%m%d).tar.gz user_data/

# Backup configuration
cp docker-compose.yml .htpasswd scrapper-config-backup/
```

#### Automated Backup
```bash
#!/bin/bash
# backup-scrapper.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/scrapper"
DATA_DIR="/data/scrapper"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup data with compression
tar -czf "$BACKUP_DIR/scrapper-data-$DATE.tar.gz" -C "$DATA_DIR" .

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "scrapper-data-*.tar.gz" -mtime +7 -delete

echo "Backup completed: scrapper-data-$DATE.tar.gz"
```

#### Restore Process
```bash
# Stop Scrapper
docker-compose down

# Restore data
cd /data/scrapper
tar -xzf /backups/scrapper/scrapper-data-20240101_120000.tar.gz

# Set permissions
chown -R 1001:1001 .

# Restart Scrapper
docker-compose up -d
```

### Database Considerations

Scrapper uses file-based storage, eliminating database dependencies:
- **Job metadata**: JSON files in job directories
- **Page content**: Individual JSON files per page
- **Job registry**: Single JSON file for domain mapping
- **Logs**: Text files per job

This design provides:
- **Simplicity**: No database setup or maintenance
- **Portability**: Easy to backup and move
- **Scalability**: Distributed across domains and jobs
- **Resilience**: Individual job failures don't affect others

## Troubleshooting

### Common Issues

#### High Memory Usage
```bash
# Check memory usage
docker stats scrapper

# Reduce browser contexts
docker-compose down
# Edit docker-compose.yml: BROWSER_CONTEXT_LIMIT=10
docker-compose up -d
```

#### Slow Crawling Performance
```bash
# Check current settings
curl http://localhost:3000/ping

# Increase concurrency
# Edit docker-compose.yml: CRAWL_MAX_CONCURRENCY=8
docker-compose restart
```

#### Permission Issues
```bash
# Fix permissions on host
sudo chown -R 1001:1001 user_data/

# Or for macOS/Windows
# Just ensure directories exist - Docker handles permissions
mkdir -p user_data user_scripts
```

#### Network Connectivity
```bash
# Test from container
docker exec scrapper curl -I https://example.com

# Check DNS resolution
docker exec scrapper nslookup example.com

# Verify proxy settings (if applicable)
docker exec scrapper env | grep -i proxy
```

### Debug Mode

Enable debug logging for troubleshooting:
```yaml
environment:
  - DEBUG=true
  - LOG_LEVEL=debug
```

### Performance Monitoring

Monitor key metrics:
```bash
# Container resources
docker stats scrapper

# Crawl job status
curl http://localhost:3000/api/crawl/ | jq

# System health
curl http://localhost:3000/ping | jq
```

## Best Practices

### Deployment
1. **Use Docker Compose**: Easier management and configuration
2. **Set Resource Limits**: Prevent resource exhaustion
3. **Enable Health Checks**: Monitor service availability
4. **Configure Logging**: Structured logging for debugging
5. **Regular Backups**: Protect crawled data

### Security
1. **Enable Authentication**: Protect access to the interface
2. **Use HTTPS**: Encrypt traffic in production
3. **Firewall Rules**: Restrict network access
4. **Regular Updates**: Keep Docker image current
5. **Monitor Access**: Log and review access patterns

### Performance
1. **Right-size Resources**: Match hardware to workload
2. **Tune Concurrency**: Balance speed with resource usage
3. **Monitor Progress**: Watch for bottlenecks
4. **Clean Up Data**: Remove old jobs regularly
5. **Optimize Settings**: Adjust based on target websites

### Maintenance
1. **Regular Health Checks**: Monitor service status
2. **Log Review**: Check for errors and warnings
3. **Capacity Planning**: Monitor disk and memory usage
4. **Update Schedule**: Plan for regular updates
5. **Documentation**: Keep deployment docs current

This deployment guide provides the foundation for running Scrapper effectively in any environment, from development to large-scale production deployments.