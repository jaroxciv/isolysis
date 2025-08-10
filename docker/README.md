# Isolysis Docker Setup

Easy Docker deployment for the complete Isolysis application stack.

## Quick Start

1. **Navigate to docker directory:**
   ```bash
   cd docker
   ```

2. **Set up environment (optional):**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (leave empty for OSMnx-only usage)
   ```

3. **Start the application:**
   ```bash
   docker compose up -d
   ```

4. **Access the application:**
   - **Streamlit Interface:** http://localhost:8501
   - **API Documentation:** http://localhost:8000/docs
   - **API Health Check:** http://localhost:8000/health

## Services

### API Service (Port 8000)
- **Container:** `isolysis-api`
- **Health Check:** Automatic health monitoring
- **Environment:** Configurable API keys via `.env`

### Streamlit Service (Port 8501)
- **Container:** `isolysis-streamlit`
- **Depends on:** API service (waits for health check)
- **Auto-configured:** Points to internal API service

## Management Commands

```bash
# Start services in background
docker compose up -d

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f api
docker compose logs -f streamlit

# Stop services
docker compose down

# Rebuild and restart
docker compose up -d --build

# Check service status
docker compose ps
```

## Environment Variables

The application supports these optional environment variables:

- `MAPBOX_API_KEY`: Global coverage with real traffic data
- `ISO4APP_API_KEY`: European coverage with high precision

**Note:** OSMnx provider works without any API keys and provides global coverage using OpenStreetMap data.

## Troubleshooting

### API Service Won't Start
```bash
# Check API logs
docker compose logs api

# Common issues:
# 1. Port 8000 already in use
# 2. Invalid API keys (check .env file)
```

### Streamlit Can't Connect to API
```bash
# Check if API is healthy
curl http://localhost:8000/health

# Check Streamlit logs
docker compose logs streamlit

# Restart services
docker compose restart
```

### Port Conflicts
If ports 8000 or 8501 are in use, modify `docker-compose.yml`:

```yaml
ports:
  - "9000:8000"  # Use port 9000 instead of 8000
  - "9501:8501"  # Use port 9501 instead of 8501
```

## Development

For development with live code changes:

```bash
# Mount local code as volumes (add to docker-compose.yml)
volumes:
  - ../api:/app/api
  - ../isolysis:/app/isolysis
  - ../st_app.py:/app/st_app.py
```

## Network Architecture

```
┌─────────────────┐    ┌──────────────────┐
│  Streamlit App  │───▶   FastAPI        │
│  Port: 8501     │    │   Port: 8000     │
│                 │    │                  │
│  User Interface │    │  REST API +      │
│  + Map Display  │    │  Spatial Analysis│
└─────────────────┘    └──────────────────┘
         │                       │
         │              ┌────────▼────────┐
         │              │   Isolysis      │
         │              │   Core Engine   │
         │              │                 │
         │              │ • OSMnx         │
         └──────────────▶ • Mapbox       │
                        │ • Iso4App       │
                        └─────────────────┘
```

## Production Deployment

For production use, consider:

1. **Environment-specific configs:**
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

2. **Reverse proxy setup** (nginx/traefik)
3. **SSL termination**
4. **Resource limits:**
   ```yaml
   deploy:
     resources:
       limits:
         memory: 1G
         cpus: '0.5'
   ```

5. **Volume persistence** for caching and outputs

## Support

- **Application Issues:** Check logs with `docker compose logs`
- **Container Issues:** Use `docker compose ps` and `docker system df`
- **Network Issues:** Verify with `docker network ls`