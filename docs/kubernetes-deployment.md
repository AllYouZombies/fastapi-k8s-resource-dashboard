# Развертывание в Kubernetes

Данное руководство описывает процесс развертывания Kubernetes Resource Monitor в кластере Kubernetes.

## Предварительные требования

- Кластер Kubernetes (версия 1.20+)
- kubectl, настроенный для работы с кластером
- Prometheus, развернутый в кластере (опционально, но рекомендуется)
- Docker registry для хранения образа приложения

## Подготовка образа

### Сборка Docker образа

```bash
# Сборка образа
docker build -f docker/Dockerfile -t k8s-resource-monitor:latest .

# Тегирование для registry
docker tag k8s-resource-monitor:latest your-registry.com/k8s-resource-monitor:latest

# Загрузка в registry
docker push your-registry.com/k8s-resource-monitor:latest
```

## Развертывание

### 1. Создание namespace

```bash
# Создание namespace для приложения
kubectl create namespace monitoring

# Или применение из файла
kubectl apply -f k8s/namespace.yaml
```

### 2. Настройка RBAC

Приложению требуются минимальные права для чтения информации о подах:

```bash
kubectl apply -f k8s/rbac.yaml
```

Файл `k8s/rbac.yaml` содержит:
- ServiceAccount для приложения
- ClusterRole с правами на чтение подов, нод и namespace'ов
- ClusterRoleBinding для связи ServiceAccount и ClusterRole

### 3. Настройка конфигурации

Создайте ConfigMap с настройками приложения:

```bash
kubectl create configmap k8s-monitor-config \
  --from-literal=PROMETHEUS_URL=http://kube-prometheus-stack-prometheus.monitoring-system.svc:9090 \
  --from-literal=LOG_LEVEL=INFO \
  --from-literal=COLLECTION_INTERVAL_MINUTES=5 \
  --from-literal=RETENTION_DAYS=1 \
  -n monitoring
```

Или создайте файл `k8s/configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: k8s-monitor-config
  namespace: monitoring
data:
  PROMETHEUS_URL: "http://kube-prometheus-stack-prometheus.monitoring-system.svc:9090"
  LOG_LEVEL: "INFO"
  COLLECTION_INTERVAL_MINUTES: "5"
  RETENTION_DAYS: "1"
  EXCLUDED_NAMESPACES: "kube-system,kube-public,kube-node-lease"
```

### 4. Развертывание приложения

Отредактируйте `k8s/deployment.yaml` и укажите правильный образ:

```yaml
spec:
  template:
    spec:
      containers:
      - name: monitor
        image: your-registry.com/k8s-resource-monitor:latest  # Измените на ваш образ
```

Примените манифесты:

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

### 5. Проверка развертывания

```bash
# Проверка статуса подов
kubectl get pods -n monitoring

# Просмотр логов
kubectl logs -f deployment/k8s-resource-monitor -n monitoring

# Проверка сервиса
kubectl get svc -n monitoring

# Проверка health check'а
kubectl exec -it deployment/k8s-resource-monitor -n monitoring -- curl http://localhost:8000/health
```

## Доступ к приложению

### Через порт-форвардинг

```bash
kubectl port-forward svc/k8s-resource-monitor 8000:80 -n monitoring
```

Приложение будет доступно по адресу: http://localhost:8000

### Через Ingress

Создайте Ingress для внешнего доступа:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: k8s-monitor-ingress
  namespace: monitoring
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: k8s-monitor.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: k8s-resource-monitor
            port:
              number: 80
```

### Через NodePort

Измените тип сервиса в `k8s/service.yaml`:

```yaml
spec:
  type: NodePort
  ports:
  - port: 80
    targetPort: 8000
    nodePort: 30800  # порт на узлах кластера
```

## Настройка мониторинга

### Prometheus ServiceMonitor

Если используется Prometheus Operator, создайте ServiceMonitor:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: k8s-resource-monitor
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: k8s-resource-monitor
  endpoints:
  - port: http
    path: /metrics
```

### Health checks

Kubernetes будет автоматически проверять здоровье приложения:

- **Liveness probe**: `/health/liveness`
- **Readiness probe**: `/health/readiness`

## Масштабирование

### Горизонтальное масштабирование

```bash
# Увеличение количества реплик
kubectl scale deployment k8s-resource-monitor --replicas=3 -n monitoring

# Автоматическое масштабирование
kubectl autoscale deployment k8s-resource-monitor --cpu-percent=70 --min=2 --max=5 -n monitoring
```

**Важно**: Приложение использует фоновые задачи для сбора данных. При масштабировании убедитесь, что только один экземпляр выполняет сбор данных, или настройте лидер-выборы.

### Вертикальное масштабирование

Настройте ресурсы в `deployment.yaml`:

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

## Обновление

### Rolling update

```bash
# Обновление образа
kubectl set image deployment/k8s-resource-monitor monitor=your-registry.com/k8s-resource-monitor:v2.0.0 -n monitoring

# Проверка статуса обновления
kubectl rollout status deployment/k8s-resource-monitor -n monitoring

# Откат к предыдущей версии (при необходимости)
kubectl rollout undo deployment/k8s-resource-monitor -n monitoring
```

## Резервное копирование

### База данных

Поскольку приложение использует SQLite, база данных хранится внутри пода. Для сохранения данных:

1. **Persistent Volume**: Подключите PV для хранения базы данных
2. **Экспорт данных**: Используйте API `/api/metrics` для экспорта данных
3. **Регулярные снимки**: Настройте автоматическое создание снимков данных

### Пример с Persistent Volume

```yaml
# В deployment.yaml добавьте:
spec:
  template:
    spec:
      containers:
      - name: monitor
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: k8s-monitor-pvc
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: k8s-monitor-pvc
  namespace: monitoring
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

## Устранение неисправностей

### Общие проблемы

1. **Нет доступа к Kubernetes API**
   ```bash
   kubectl logs deployment/k8s-resource-monitor -n monitoring | grep "Kubernetes"
   ```

2. **Нет подключения к Prometheus**
   ```bash
   kubectl logs deployment/k8s-resource-monitor -n monitoring | grep "Prometheus"
   ```

3. **Проблемы с правами RBAC**
   ```bash
   kubectl auth can-i get pods --as=system:serviceaccount:monitoring:k8s-resource-monitor
   ```

### Полезные команды

```bash
# Подробная информация о поде
kubectl describe pod -l app=k8s-resource-monitor -n monitoring

# Вход в контейнер для отладки
kubectl exec -it deployment/k8s-resource-monitor -n monitoring -- /bin/bash

# Просмотр событий
kubectl get events -n monitoring --sort-by='.lastTimestamp'

# Проверка сетевых политик
kubectl get networkpolicies -n monitoring
```