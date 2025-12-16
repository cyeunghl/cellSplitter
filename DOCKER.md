# Docker Deployment Guide

This guide explains how to run the CellSplitter application using Docker.

## Prerequisites

- Docker installed on your system
- Docker Compose (optional, but recommended)

## Quick Start with Docker Compose

The easiest way to run the application is using Docker Compose:

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

The application will be available at `http://localhost:5002`

## Manual Docker Commands

If you prefer to use Docker directly without Docker Compose:

### Build the Image

```bash
docker build -t cellsplitter:latest .
```

### Run the Container

```bash
docker run -d \
  --name cellsplitter-app \
  -p 5002:5002 \
  -v $(pwd)/instance:/app/instance \
  -v $(pwd)/data:/app/data \
  cellsplitter:latest
```

### Manage the Container

```bash
# View logs
docker logs -f cellsplitter-app

# Stop the container
docker stop cellsplitter-app

# Start the container
docker start cellsplitter-app

# Remove the container
docker rm -f cellsplitter-app
```

## Configuration

### Port Configuration

The application runs on port 5002 by default. You can change this by:

1. **Using Docker Compose**: Edit the `ports` section in `docker-compose.yml`
   ```yaml
   ports:
     - "8080:5002"  # Maps host port 8080 to container port 5002
   ```

2. **Using Docker run**: Change the port mapping
   ```bash
   docker run -p 8080:5002 cellsplitter:latest
   ```

### Data Persistence

The SQLite database is stored in the `instance` directory, which is mounted as a Docker volume. This ensures your data persists even when the container is stopped or removed.

### Environment Variables

You can customize the application using environment variables:

```yaml
environment:
  - FLASK_APP=app.py
  - FLASK_ENV=production
  - PORT=5002
```

## Troubleshooting

### Check if the container is running

```bash
docker ps
```

### View container logs

```bash
docker logs cellsplitter-app
```

### Access the container shell

```bash
docker exec -it cellsplitter-app /bin/bash
```

### Rebuild after code changes

```bash
# With Docker Compose
docker-compose up -d --build

# With Docker
docker build -t cellsplitter:latest .
docker stop cellsplitter-app
docker rm cellsplitter-app
docker run -d --name cellsplitter-app -p 5002:5002 -v $(pwd)/instance:/app/instance cellsplitter:latest
```

## Health Check

The application includes a health check that runs every 30 seconds. You can check the health status:

```bash
docker inspect --format='{{.State.Health.Status}}' cellsplitter-app
```

## Production Recommendations

For production deployments:

1. Use a production WSGI server like Gunicorn:
   - Update `requirements.txt` to include `gunicorn`
   - Modify the CMD in Dockerfile to: `CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5002", "app:app"]`

2. Set `FLASK_ENV=production` in your environment variables

3. Consider using PostgreSQL instead of SQLite for better concurrency

4. Set up proper logging and monitoring

5. Use secrets management for the `SECRET_KEY` instead of hardcoding it
