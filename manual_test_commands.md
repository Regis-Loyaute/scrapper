# Manual Test Commands for homelabing.com

## Quick Health Check
```bash
curl http://localhost:3000/ping
```

## Basic Article Extraction
```bash
curl "http://localhost:3000/api/article?url=https://homelabing.com"
```

## Article with Screenshot
```bash
curl "http://localhost:3000/api/article?url=https://homelabing.com&screenshot=true"
```

## Article with Full Content
```bash
curl "http://localhost:3000/api/article?url=https://homelabing.com&full-content=true"
```

## Links Extraction
```bash
curl "http://localhost:3000/api/links?url=https://homelabing.com"
```

## Test Specific Page
```bash
# Test a specific blog post
curl "http://localhost:3000/api/article?url=https://homelabing.com/posts/"
```

## Advanced Options
```bash
# With browser parameters
curl "http://localhost:3000/api/article?url=https://homelabing.com&device=Desktop+Chrome&timeout=30000&sleep=2000"

# With custom readability settings
curl "http://localhost:3000/api/article?url=https://homelabing.com&char-threshold=300&nb-top-candidates=10"
```

## Expected Results

### Successful Article Response:
```json
{
  "title": "Home Assistant, Docker, Proxmox, and more",
  "content": "<article><h1>...</h1><p>...</p></article>",
  "textContent": "...",
  "url": "https://homelabing.com/",
  "domain": "homelabing.com",
  "length": 1234,
  "date": "2025-08-17T15:...",
  "id": "...",
  "resultUri": "...",
  "meta": {...}
}
```

### Successful Links Response:
```json
{
  "title": "Home Assistant, Docker, Proxmox, and more",
  "url": "https://homelabing.com/",
  "domain": "homelabing.com",
  "links": [
    {"url": "https://homelabing.com/posts/...", "text": "..."},
    ...
  ],
  "date": "2025-08-17T15:...",
  "id": "...",
  "resultUri": "..."
}
```

## Troubleshooting

### If you get AttributeError:
- Check container logs: `docker-compose logs scrapper`
- Restart container: `docker-compose restart`

### If you get 422 Validation Error:
- URL parameter is required
- Check URL is properly encoded

### If you get timeout:
- Increase timeout: `&timeout=60000`
- Add sleep for slow sites: `&sleep=3000`

### If content is empty:
- Try different browser: `&device=Desktop+Firefox`
- Lower thresholds: `&char-threshold=100`
- Check if site requires JavaScript

## Performance Testing
```bash
# Time the request
time curl "http://localhost:3000/api/article?url=https://homelabing.com"

# Test with cache
curl "http://localhost:3000/api/article?url=https://homelabing.com&cache=true"
```