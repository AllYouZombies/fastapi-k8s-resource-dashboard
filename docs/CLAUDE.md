# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Quick start (production-ready):**
```bash
cp .env.example .env
# Edit PROMETHEUS_URL in .env
./start.sh
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

**Deploy to Kubernetes:**
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/rbac.yaml  
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

## Architecture Overview

This is a FastAPI-based Kubernetes resource monitoring application with the following key architectural patterns:

### Core Components

1. **Configuration Management** (`app/core/config.py`)
   - Uses pydantic-settings for environment-based configuration
   - Centralizes all application settings including K8s, Prometheus, and database config

2. **Service Layer Architecture**
   - `KubernetesService`: Async client for K8s API, handles pod resource collection
   - `PrometheusService`: HTTP client for metrics collection via PromQL queries
   - `ResourceCollectorService`: Orchestrates data collection from both sources

3. **Background Task System** (`app/core/scheduler.py`)
   - Uses APScheduler for periodic resource collection (default: 5 minutes)
   - Implements lifespan management for FastAPI
   - Prevents overlapping collection runs with max_instances=1

4. **Data Model** (`app/models/database.py`)
   - `ResourceMetric`: Time-series data for pod resource requests/limits and actual usage
   - `ResourceSummary`: Aggregated data by namespace
   - Optimized indexes for timestamp, pod_name, and namespace queries

5. **Web Dashboard** (`app/api/routes/dashboard.py`)
   - Multi-table view: CPU requests vs usage, CPU limits vs usage, Memory requests vs usage, Memory limits vs usage
   - Real-time charts using Chart.js
   - Pagination (20 records/page), search, and namespace filtering

### Data Flow

1. **Collection**: Background scheduler triggers ResourceCollectorService every 5 minutes
2. **K8s Data**: KubernetesService fetches pod specs (requests/limits) from all namespaces except system namespaces
3. **Prometheus Data**: PrometheusService queries actual CPU/memory usage metrics
4. **Storage**: Combined data stored in SQLite with 1-day retention
5. **Presentation**: Web dashboard serves paginated, searchable tables and real-time charts

### Configuration

The application is configured via environment variables or `.env` file:
- `K8S_IN_CLUSTER`: Boolean for in-cluster vs external K8s access
- `PROMETHEUS_URL`: Prometheus server endpoint (default: kube-prometheus-stack service)
- `DATABASE_URL`: SQLite database path
- `COLLECTION_INTERVAL_MINUTES`: Background collection frequency
- `EXCLUDED_NAMESPACES`: List of namespaces to ignore (defaults to K8s system namespaces)

### Key Design Patterns

- **Async/await throughout**: All I/O operations are asynchronous
- **Resource parsing**: Custom CPU (cores/millicores) and memory (bytes with K/M/G/T suffixes) parsers
- **Context managers**: Proper resource cleanup for HTTP clients and K8s API clients  
- **Database indexing**: Composite indexes optimized for time-series queries
- **Error handling**: Structured logging with correlation for debugging

This architecture supports production deployment with proper RBAC, health checks, and horizontal scaling capabilities.