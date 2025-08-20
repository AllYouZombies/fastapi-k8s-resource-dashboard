# Развертывание с Docker

Руководство по запуску Kubernetes Resource Monitor с использованием Docker и Docker Compose.

## Docker

### Сборка образа

```bash
# Сборка образа из корневой директории проекта
docker build -f docker/Dockerfile -t k8s-resource-monitor:latest .

# Сборка с тегом версии
docker build -f docker/Dockerfile -t k8s-resource-monitor:v1.0.0 .
```

### Запуск контейнера

#### Простой запуск

```bash
docker run -d \
  --name k8s-resource-monitor \
  -p 8000:8000 \
  -v ~/.kube/config:/app/.kube/config:ro \
  -e K8S_IN_CLUSTER=false \
  -e K8S_CONFIG_PATH=/app/.kube/config \
  -e PROMETHEUS_URL=http://your-prometheus:9090 \
  k8s-resource-monitor:latest
```

#### Запуск с дополнительными настройками

```bash
docker run -d \
  --name k8s-resource-monitor \
  -p 8000:8000 \
  -v ~/.kube/config:/app/.kube/config:ro \
  -v $(pwd)/data:/app/data \
  -e K8S_IN_CLUSTER=false \
  -e K8S_CONFIG_PATH=/app/.kube/config \
  -e PROMETHEUS_URL=http://prometheus.example.com:9090 \
  -e DATABASE_URL=sqlite:///app/data/k8s_metrics.db \
  -e LOG_LEVEL=INFO \
  -e COLLECTION_INTERVAL_MINUTES=5 \
  -e RETENTION_DAYS=1 \
  --restart unless-stopped \
  k8s-resource-monitor:latest
```

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `K8S_IN_CLUSTER` | Запуск внутри кластера K8s | `true` |
| `K8S_CONFIG_PATH` | Путь к kubeconfig файлу | `None` |
| `PROMETHEUS_URL` | URL Prometheus сервера | `http://kube-prometheus-stack-prometheus.monitoring-system.svc:9090` |
| `DATABASE_URL` | URL базы данных SQLite | `sqlite:///./k8s_metrics.db` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `COLLECTION_INTERVAL_MINUTES` | Интервал сбора в минутах | `5` |
| `RETENTION_DAYS` | Период хранения данных в днях | `1` |
| `EXCLUDED_NAMESPACES` | Исключаемые namespace'ы | `kube-system,kube-public,kube-node-lease` |

## Docker Compose

### docker-compose.yml

Создайте файл `docker-compose.yml` в корневой директории:

```yaml
version: '3.8'

services:
  k8s-resource-monitor:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: k8s-resource-monitor
    ports:
      - "8000:8000"
    volumes:
      - ~/.kube/config:/app/.kube/config:ro
      - ./data:/app/data
    environment:
      - K8S_IN_CLUSTER=false
      - K8S_CONFIG_PATH=/app/.kube/config
      - PROMETHEUS_URL=http://prometheus:9090
      - DATABASE_URL=sqlite:///app/data/k8s_metrics.db
      - LOG_LEVEL=INFO
      - COLLECTION_INTERVAL_MINUTES=5
      - RETENTION_DAYS=1
    restart: unless-stopped
    depends_on:
      - prometheus
    networks:
      - monitoring

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    restart: unless-stopped
    networks:
      - monitoring

volumes:
  prometheus_data:

networks:
  monitoring:
    driver: bridge
```

### .env файл

Создайте файл `.env` для переменных окружения:

```bash
# Kubernetes настройки
K8S_IN_CLUSTER=false
K8S_CONFIG_PATH=/app/.kube/config

# Prometheus настройки
PROMETHEUS_URL=http://prometheus:9090

# База данных
DATABASE_URL=sqlite:///app/data/k8s_metrics.db

# Настройки приложения
LOG_LEVEL=INFO
COLLECTION_INTERVAL_MINUTES=5
RETENTION_DAYS=1
EXCLUDED_NAMESPACES=kube-system,kube-public,kube-node-lease

# Настройки веб-сервера
CORS_ORIGINS=*
PAGE_SIZE=20
```

### Запуск с Docker Compose

```bash
# Запуск всех сервисов
docker-compose up -d

# Запуск только k8s-resource-monitor
docker-compose up -d k8s-resource-monitor

# Просмотр логов
docker-compose logs -f k8s-resource-monitor

# Остановка сервисов
docker-compose down

# Пересборка образов
docker-compose build --no-cache
```

## Развертывание в продуктивной среде

### Мульти-стейдж Docker файл

Создайте оптимизированный Dockerfile:

```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -r -s /bin/bash -m -d /app appuser

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY app/ ./app/
COPY --chown=appuser:appuser . .

# Make sure scripts are executable
RUN chmod +x /home/appuser/.local/bin/*

# Switch to non-root user
USER appuser

# Update PATH
ENV PATH="/home/appuser/.local/bin:$PATH"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/liveness || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Настройка логирования

Создайте конфигурацию логирования `logging.yaml`:

```yaml
version: 1
disable_existing_loggers: false

formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  json:
    format: '{"time": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: default
    stream: ext://sys.stdout
  
  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: json
    filename: /app/data/app.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

loggers:
  app:
    level: INFO
    handlers: [console, file]
    propagate: no

root:
  level: INFO
  handlers: [console]
```

### Производственный docker-compose.yml

```yaml
version: '3.8'

services:
  k8s-resource-monitor:
    build:
      context: .
      dockerfile: docker/Dockerfile.prod
    image: k8s-resource-monitor:prod
    container_name: k8s-resource-monitor
    ports:
      - "8000:8000"
    volumes:
      - ~/.kube/config:/app/.kube/config:ro
      - ./data:/app/data
      - ./logs:/app/logs
      - ./logging.yaml:/app/logging.yaml:ro
    env_file:
      - .env.prod
    restart: unless-stopped
    networks:
      - monitoring
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'

  nginx:
    image: nginx:alpine
    container_name: k8s-monitor-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - k8s-resource-monitor
    restart: unless-stopped
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge
```

### Nginx конфигурация

Создайте `nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream app {
        server k8s-resource-monitor:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        location /health {
            proxy_pass http://app;
            access_log off;
        }
    }
}
```

## Мониторинг и отладка

### Просмотр логов

```bash
# Логи контейнера
docker logs -f k8s-resource-monitor

# Логи через Docker Compose
docker-compose logs -f k8s-resource-monitor

# Последние 100 строк логов
docker logs --tail 100 k8s-resource-monitor
```

### Отладка внутри контейнера

```bash
# Вход в контейнер
docker exec -it k8s-resource-monitor /bin/bash

# Проверка процессов
docker exec k8s-resource-monitor ps aux

# Проверка сетевых подключений
docker exec k8s-resource-monitor netstat -tulpn

# Тест подключения к Prometheus
docker exec k8s-resource-monitor curl -I http://prometheus:9090
```

### Мониторинг ресурсов

```bash
# Статистика контейнера
docker stats k8s-resource-monitor

# Информация о контейнере
docker inspect k8s-resource-monitor

# Использование дискового пространства
docker exec k8s-resource-monitor df -h
```

## Резервное копирование

### Backup скрипт

Создайте скрипт `backup.sh`:

```bash
#!/bin/bash

CONTAINER_NAME="k8s-resource-monitor"
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"

mkdir -p $BACKUP_DIR

# Backup database
docker cp $CONTAINER_NAME:/app/data/k8s_metrics.db $BACKUP_DIR/

# Backup logs
docker cp $CONTAINER_NAME:/app/logs $BACKUP_DIR/

# Backup configuration
cp .env $BACKUP_DIR/
cp docker-compose.yml $BACKUP_DIR/

echo "Backup completed: $BACKUP_DIR"
```

### Автоматическое резервное копирование

Добавьте в cron:

```bash
# Backup every day at 2 AM
0 2 * * * /path/to/backup.sh >> /var/log/k8s-monitor-backup.log 2>&1
```