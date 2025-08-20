# Мониторинг и обслуживание

Руководство по мониторингу, обслуживанию и устранению проблем Kubernetes Resource Monitor.

## Мониторинг состояния системы

### Health Check эндпоинты

Система предоставляет несколько эндпоинтов для проверки состояния:

#### `/health`
Полная проверка всех компонентов:
```bash
curl http://localhost:8000/health
```

Ответ:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "database_status": "healthy",
  "kubernetes_status": "healthy",
  "prometheus_status": "healthy"
}
```

#### `/health/liveness`
Проверка, что приложение запущено:
```bash
curl http://localhost:8000/health/liveness
```

#### `/health/readiness`
Проверка готовности к обработке запросов:
```bash
curl http://localhost:8000/health/readiness
```

### Kubernetes Probes

В Kubernetes настройте probes:

```yaml
livenessProbe:
  httpGet:
    path: /health/liveness
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/readiness
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 2
```

## Метрики приложения

### Встроенные метрики

Система собирает внутренние метрики:

- Количество собранных pod'ов
- Время выполнения запросов к Kubernetes API
- Время выполнения запросов к Prometheus
- Размер базы данных
- Количество ошибок

### Prometheus метрики

Добавьте экспорт метрик в `main.py`:

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time

# Метрики
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active connections')
PODS_COLLECTED = Gauge('pods_collected_total', 'Total number of pods collected')
COLLECTION_DURATION = Histogram('collection_duration_seconds', 'Collection duration')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    REQUEST_DURATION.observe(duration)
    
    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Grafana Dashboard

Создайте dashboard для визуализации метрик:

```json
{
  "dashboard": {
    "title": "K8s Resource Monitor",
    "panels": [
      {
        "title": "HTTP Requests Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Collection Duration",
        "type": "graph", 
        "targets": [
          {
            "expr": "collection_duration_seconds",
            "legendFormat": "Collection Time"
          }
        ]
      },
      {
        "title": "Pods Collected",
        "type": "singlestat",
        "targets": [
          {
            "expr": "pods_collected_total",
            "legendFormat": "Pods"
          }
        ]
      }
    ]
  }
}
```

## Логирование

### Структурированное логирование

Настройте JSON логирование для лучшего анализа:

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)

# Настройка в main.py
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

for handler in logging.root.handlers:
    handler.setFormatter(JSONFormatter())
```

### Централизованное логирование

#### ELK Stack

```yaml
# filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /app/logs/*.log
  fields:
    service: k8s-resource-monitor
  json.keys_under_root: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
```

#### Fluentd

```yaml
<source>
  @type tail
  path /app/logs/*.log
  pos_file /fluentd/log/k8s-monitor.log.pos
  tag k8s-resource-monitor
  format json
</source>

<match k8s-resource-monitor>
  @type elasticsearch
  host elasticsearch
  port 9200
  index_name k8s-resource-monitor
</match>
```

## Резервное копирование

### Автоматическое резервное копирование

Создайте скрипт `backup.sh`:

```bash
#!/bin/bash

# Конфигурация
BACKUP_DIR="/backup/k8s-resource-monitor"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$DATE"
RETENTION_DAYS=7

# Создание директории для резервной копии
mkdir -p $BACKUP_PATH

# Резервное копирование базы данных
if [ -f "/app/data/k8s_metrics.db" ]; then
    sqlite3 /app/data/k8s_metrics.db ".backup $BACKUP_PATH/k8s_metrics.db"
    echo "Database backup created: $BACKUP_PATH/k8s_metrics.db"
fi

# Резервное копирование конфигурации
cp /app/.env $BACKUP_PATH/ 2>/dev/null || true
cp /app/logging.yaml $BACKUP_PATH/ 2>/dev/null || true

# Резервное копирование логов
cp -r /app/logs $BACKUP_PATH/ 2>/dev/null || true

# Сжатие резервной копии
cd $BACKUP_DIR
tar -czf "$DATE.tar.gz" $DATE/
rm -rf $DATE/

# Удаление старых резервных копий
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $BACKUP_DIR/$DATE.tar.gz"
```

### Kubernetes CronJob для резервного копирования

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: k8s-monitor-backup
  namespace: monitoring
spec:
  schedule: "0 2 * * *"  # каждый день в 2:00
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: alpine:3.18
            command:
            - /bin/sh
            - -c
            - |
              apk add --no-cache sqlite
              mkdir -p /backup
              sqlite3 /data/k8s_metrics.db ".backup /backup/k8s_metrics_$(date +%Y%m%d_%H%M%S).db"
            volumeMounts:
            - name: data-volume
              mountPath: /data
            - name: backup-volume
              mountPath: /backup
          volumes:
          - name: data-volume
            persistentVolumeClaim:
              claimName: k8s-monitor-data
          - name: backup-volume
            persistentVolumeClaim:
              claimName: k8s-monitor-backup
          restartPolicy: OnFailure
```

## Масштабирование

### Вертикальное масштабирование

Мониторинг ресурсов:

```bash
# CPU и память пода
kubectl top pod k8s-resource-monitor-xxx -n monitoring

# Детальная информация
kubectl describe pod k8s-resource-monitor-xxx -n monitoring
```

Увеличение лимитов ресурсов:

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1500m"
```

### Горизонтальное масштабирование

**Важно**: Приложение использует фоновые задачи. При горизонтальном масштабировании нужно обеспечить, что только один экземпляр выполняет сбор данных.

Реализация лидер-выборов:

```python
import asyncio
from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.rest import ApiException

class LeaderElection:
    def __init__(self, name: str, namespace: str):
        self.name = name
        self.namespace = namespace
        self.is_leader = False
        
    async def acquire_leadership(self):
        try:
            v1 = client.CoreV1Api()
            
            # Попытка создания ConfigMap для лидерства
            body = client.V1ConfigMap(
                metadata=client.V1ObjectMeta(name=self.name),
                data={"leader": "current-pod-name"}
            )
            
            await v1.create_namespaced_config_map(
                namespace=self.namespace,
                body=body
            )
            self.is_leader = True
            
        except ApiException as e:
            if e.status == 409:  # Already exists
                self.is_leader = False
            else:
                raise
                
    async def release_leadership(self):
        if self.is_leader:
            v1 = client.CoreV1Api()
            await v1.delete_namespaced_config_map(
                name=self.name,
                namespace=self.namespace
            )
            self.is_leader = False

# Использование в scheduler.py
leader_election = LeaderElection("k8s-resource-monitor-leader", "monitoring")

async def collect_resources():
    await leader_election.acquire_leadership()
    if leader_election.is_leader:
        # Выполнение сбора данных
        pass
```

## Обновление приложения

### Rolling Update в Kubernetes

```bash
# Обновление образа
kubectl set image deployment/k8s-resource-monitor \
  monitor=your-registry.com/k8s-resource-monitor:v2.0.0 \
  -n monitoring

# Проверка статуса обновления
kubectl rollout status deployment/k8s-resource-monitor -n monitoring

# Откат при необходимости
kubectl rollout undo deployment/k8s-resource-monitor -n monitoring
```

### Blue-Green развертывание

```bash
# Создание новой версии
kubectl apply -f k8s/deployment-green.yaml

# Переключение трафика
kubectl patch service k8s-resource-monitor -p '{"spec":{"selector":{"version":"green"}}}'

# Удаление старой версии
kubectl delete deployment k8s-resource-monitor-blue
```

## Устранение неисправностей

### Частые проблемы

#### 1. Подключение к Kubernetes API

**Симптомы**: Ошибки "Unable to connect to Kubernetes API"

**Диагностика**:
```bash
kubectl logs deployment/k8s-resource-monitor -n monitoring | grep -i kubernetes
```

**Решение**:
- Проверить права ServiceAccount
- Убедиться в корректности kubeconfig
- Проверить сетевую доступность API сервера

#### 2. Подключение к Prometheus

**Симптомы**: Ошибки "Prometheus connection failed"

**Диагностика**:
```bash
# Проверка доступности Prometheus
kubectl exec -it deployment/k8s-resource-monitor -n monitoring -- \
  curl -I http://prometheus:9090

# Проверка DNS разрешения
kubectl exec -it deployment/k8s-resource-monitor -n monitoring -- \
  nslookup prometheus
```

**Решение**:
- Проверить URL Prometheus
- Убедиться в доступности сервиса
- Проверить Network Policies

#### 3. Проблемы с базой данных

**Симптомы**: Ошибки "Database connection failed"

**Диагностика**:
```bash
kubectl exec -it deployment/k8s-resource-monitor -n monitoring -- \
  sqlite3 /app/data/k8s_metrics.db "PRAGMA integrity_check;"
```

**Решение**:
- Проверить права доступа к файлу БД
- Убедиться в наличии свободного места
- Восстановить из резервной копии при необходимости

#### 4. Высокое потребление памяти

**Симптомы**: Pod перезапускается с OOMKilled

**Диагностика**:
```bash
kubectl top pod k8s-resource-monitor-xxx -n monitoring
kubectl describe pod k8s-resource-monitor-xxx -n monitoring
```

**Решение**:
- Увеличить лимиты памяти
- Оптимизировать запросы к базе данных
- Уменьшить интервал ротации данных

### Отладочные команды

```bash
# Проверка всех ресурсов
kubectl get all -n monitoring -l app=k8s-resource-monitor

# Детальная информация о деплойменте
kubectl describe deployment k8s-resource-monitor -n monitoring

# События в namespace
kubectl get events -n monitoring --sort-by='.lastTimestamp'

# Сетевые политики
kubectl get networkpolicies -n monitoring

# PersistentVolumeClaims
kubectl get pvc -n monitoring

# Secrets и ConfigMaps
kubectl get secrets,configmaps -n monitoring
```

### Сбор диагностической информации

Скрипт для сбора информации:

```bash
#!/bin/bash

NAMESPACE="monitoring"
APP="k8s-resource-monitor"
OUTPUT_DIR="./debug-$(date +%Y%m%d_%H%M%S)"

mkdir -p $OUTPUT_DIR

# Основная информация
kubectl get all -n $NAMESPACE -l app=$APP > $OUTPUT_DIR/resources.txt
kubectl describe deployment $APP -n $NAMESPACE > $OUTPUT_DIR/deployment.txt
kubectl describe service $APP -n $NAMESPACE > $OUTPUT_DIR/service.txt

# Логи
kubectl logs deployment/$APP -n $NAMESPACE --tail=1000 > $OUTPUT_DIR/logs.txt
kubectl logs deployment/$APP -n $NAMESPACE --previous --tail=1000 > $OUTPUT_DIR/logs-previous.txt 2>/dev/null

# События
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' > $OUTPUT_DIR/events.txt

# Конфигурация
kubectl get configmap,secret -n $NAMESPACE > $OUTPUT_DIR/config.txt

# Состояние узлов
kubectl get nodes -o wide > $OUTPUT_DIR/nodes.txt
kubectl top nodes > $OUTPUT_DIR/nodes-usage.txt

echo "Debug information collected in: $OUTPUT_DIR"
```

## Алерты и уведомления

### Prometheus AlertManager

```yaml
groups:
- name: k8s-resource-monitor
  rules:
  - alert: K8sResourceMonitorDown
    expr: up{job="k8s-resource-monitor"} == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "K8s Resource Monitor is down"
      
  - alert: K8sResourceMonitorHighMemory
    expr: container_memory_usage_bytes{pod=~"k8s-resource-monitor-.*"} > 1e9
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage in K8s Resource Monitor"
      
  - alert: CollectionFailed
    expr: increase(collection_errors_total[1h]) > 5
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Multiple collection failures detected"
```

### Интеграция с внешними системами

#### Slack уведомления

```python
import aiohttp

async def send_slack_notification(message: str):
    webhook_url = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
    
    payload = {
        "text": f"🚨 K8s Resource Monitor Alert: {message}",
        "channel": "#monitoring",
        "username": "K8s Monitor"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=payload) as response:
            return response.status == 200
```

#### Email уведомления

```python
import smtplib
from email.mime.text import MIMEText

def send_email_alert(subject: str, body: str):
    msg = MIMEText(body)
    msg['Subject'] = f"K8s Resource Monitor: {subject}"
    msg['From'] = "monitor@company.com"
    msg['To'] = "admin@company.com"
    
    server = smtplib.SMTP('smtp.company.com', 587)
    server.starttls()
    server.login("username", "password")
    server.send_message(msg)
    server.quit()
```