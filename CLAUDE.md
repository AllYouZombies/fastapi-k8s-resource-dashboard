# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Quick start (production-ready):**
```bash
cp .env.example .env
# Edit PROMETHEUS_URL in .env
./start.sh
```

**Using Make commands:**
```bash
make help          # Show all available commands
make install       # Full setup and start
make start         # Start application
make dev          # Local development mode
make logs         # View logs
make health       # Check application health
```

**Manual Docker Compose:**
```bash
cp .env.example .env
mkdir -p data logs
docker-compose up -d
```

**Development mode:**
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Code quality:**
```bash
make lint          # Check code quality (flake8, black, isort)
make format        # Format code (black, isort) 
make test          # Run tests with pytest
```

**Kubernetes deployment:**
```bash
make k8s-deploy    # Deploy to Kubernetes
make k8s-logs      # View K8s logs
make k8s-status    # Check K8s status
```

## Repository Information

**GitHub Repository:** https://github.com/AllYouZombies/fastapi-k8s-resource-dashboard

**Clone command:**
```bash
git clone https://github.com/AllYouZombies/fastapi-k8s-resource-dashboard.git
cd fastapi-k8s-resource-dashboard
```

## Architecture Overview

This is a FastAPI-based Kubernetes resource monitoring application that compares resource requests/limits with actual usage from Prometheus.

### Core Components

1. **Configuration Management** (`app/core/config.py`)
   - Uses pydantic-settings for environment-based configuration
   - Supports .env files with production defaults
   - Key settings: K8S_IN_CLUSTER, PROMETHEUS_URL, DATABASE_URL

2. **Service Layer Architecture**
   - `KubernetesService`: Async K8s API client for pod resource collection
   - `PrometheusService`: HTTP client for actual usage metrics via PromQL
   - `ResourceCollectorService`: Orchestrates data collection from both sources

3. **Background Task System** (`app/core/scheduler.py`)
   - Uses APScheduler with FastAPI lifespan management
   - Periodic collection every 5 minutes (configurable)
   - Prevents overlapping runs with max_instances=1

4. **Data Storage** (`app/models/database.py`)
   - SQLite with optimized time-series indexes
   - `ResourceMetric`: Pod resource data with actual usage
   - Configurable retention period (default 7 days)

5. **Web Interface** (`app/api/routes/dashboard.py`)
   - 4 comparative tables with logical column order: Node → Namespace → Pod → Container → Status → Resource Data
   - Historical data display: min/current/max values for actual usage and utilization percentages
   - Resource recommendations system with backend API endpoint (`/api/recommendations/{pod_name}/{container_name}`)
   - Real-time charts: 4 separate charts for CPU/Memory vs requests/limits percentages
   - AJAX-based interactions without page reloads
   - Advanced filtering: search, namespace filter, incomplete data filter (enabled by default)
   - Server-side sorting and pagination (20 records/page)

### Data Flow

1. **Collection**: Background scheduler → ResourceCollectorService every 5 minutes
2. **K8s Data**: Fetch pod specs (requests/limits) excluding system namespaces  
3. **Prometheus Data**: Query actual CPU/memory usage metrics
4. **Storage**: Combined data in SQLite with automatic cleanup
5. **Historical Analysis**: Calculate min/max/current values across entire pod lifecycle for recommendations
6. **Presentation**: Web dashboard with interactive tables, charts, and smart resource recommendations

### Key Configuration

Essential environment variables in `.env`:
- `PROMETHEUS_URL`: Prometheus server endpoint (required)
- `K8S_IN_CLUSTER`: Boolean for in-cluster vs external access
- `KUBECONFIG_PATH`: Path to kubeconfig file
- `HOST_UID`/`HOST_GID`: Host user credentials for kubeconfig access
- `COLLECTION_INTERVAL_MINUTES`: Collection frequency
- `RETENTION_DAYS`: Data retention period
- `EXCLUDED_NAMESPACES`: Namespaces to ignore (comma-separated string)

### Project Structure

```
├── start.sh              # Automated setup and launch script
├── docker-compose.yml    # Container orchestration with .env support
├── Makefile             # Development commands
├── app/                 # FastAPI application
│   ├── main.py         # Application entry point
│   ├── core/           # Configuration, database, scheduler
│   ├── services/       # Business logic (K8s, Prometheus, collection)
│   ├── models/         # SQLAlchemy and Pydantic models
│   ├── api/routes/     # FastAPI routes (dashboard, API, health)
│   └── static/         # Frontend assets (CSS, JS, templates)
├── k8s/                # Kubernetes manifests
└── docs/               # Documentation
```

### Key Design Patterns

- **Async/await throughout**: All I/O operations are asynchronous
- **Resource parsing**: Custom CPU (millicores) and memory (bytes with suffixes) parsers in KubernetesService
- **Historical data analysis**: Backend calculations of min/max/current values for accurate resource recommendations
- **Smart recommendations algorithm**: 
  - Requests based on current usage with proper rounding (50m/100m for CPU, 64Mi/128Mi/0.1Gi for memory)
  - Limits based on historical maximum with 25% headroom to prevent OOMKilled
- **Context managers**: Proper cleanup for HTTP and K8s clients
- **Environment-driven config**: Production-ready defaults with .env override
- **Health checks**: Comprehensive health endpoints for monitoring
- **Clean separation**: Services handle business logic, routes handle HTTP
- **AJAX-first frontend**: Dynamic updates without page reloads for better UX
- **Secure container setup**: Uses build args to create user with host UID/GID for kubeconfig access
- **Flexible permissions**: Handles both in-cluster and external K8s access patterns

### Docker Build Arguments

The Dockerfile uses build arguments to create a user with matching host credentials:

```dockerfile
ARG HOST_UID=1000
ARG HOST_GID=1000
RUN groupadd -r -g ${HOST_GID:-1000} appuser && \
    useradd -r -s /bin/bash -u ${HOST_UID:-1000} -g appuser -d /app appuser
```

This ensures the container can access the host's kubeconfig file. The `start.sh` script automatically detects host UID/GID and adds them to `.env`.

This architecture supports production deployment with proper RBAC, monitoring, and horizontal scaling capabilities.