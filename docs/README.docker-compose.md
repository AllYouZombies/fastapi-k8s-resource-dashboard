# Docker Compose Setup

Этот файл описывает запуск через Docker Compose. Для быстрого старта используйте `./start.sh`.

## 🚀 Автоматический запуск

```bash
# Один скрипт для всего
./start.sh
```

Скрипт автоматически:
- Проверит зависимости (Docker, kubectl)
- Создаст .env файл из шаблона
- Создаст необходимые директории
- Проверит доступ к Kubernetes
- Соберет и запустит контейнер
- Проверит готовность приложения

## 📋 Ручной запуск

```bash
# 1. Подготовка
cp .env.example .env
mkdir -p data logs

# 2. Настройка (ОБЯЗАТЕЛЬНО!)
nano .env
# Измените: PROMETHEUS_URL=http://your-prometheus:9090

# 3. Запуск
docker-compose up -d

# 4. Проверка
docker-compose logs -f
```

**Доступ к приложению:** http://localhost:8000

## Настройка

### Переменные окружения

Скопируйте и отредактируйте файл настроек:

```bash
cp .env.example .env
```

**Обязательно настройте:**

```bash
# URL вашего Prometheus сервера
PROMETHEUS_URL=http://your-prometheus-server:9090

# Если нужно, измените путь к kubeconfig
K8S_CONFIG_PATH=/app/.kube/config
```

### Подключение к Kubernetes

#### Локальный кластер (minikube, kind, etc.)

```bash
# Убедитесь, что kubeconfig доступен
ls -la ~/.kube/config

# Запуск
docker-compose up -d
```

#### Внешний кластер

```bash
# Поместите kubeconfig в ~/.kube/config или измените volume в docker-compose.yml
volumes:
  - /path/to/your/kubeconfig:/app/.kube/config:ro
```

#### Кластер в облаке

```bash
# Для AWS EKS
aws eks update-kubeconfig --name your-cluster-name

# Для GKE  
gcloud container clusters get-credentials your-cluster-name --zone your-zone

# Для Azure AKS
az aks get-credentials --resource-group your-rg --name your-cluster-name
```

### Prometheus

Приложение требует доступ к Prometheus серверу для получения метрик использования ресурсов.

**Примеры URL:**

```bash
# Prometheus в том же кластере K8s
PROMETHEUS_URL=http://kube-prometheus-stack-prometheus.monitoring.svc:9090

# Prometheus Operator
PROMETHEUS_URL=http://prometheus-operated.monitoring.svc:9090

# Внешний Prometheus
PROMETHEUS_URL=http://prometheus.example.com:9090

# Локальный Prometheus
PROMETHEUS_URL=http://host.docker.internal:9090
```

## Полезные команды

### Управление

```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart k8s-resource-monitor

# Пересборка образа
docker-compose build --no-cache

# Перезапуск с пересборкой
docker-compose up -d --build
```

### Мониторинг

```bash
# Статус контейнера
docker-compose ps

# Логи
docker-compose logs -f k8s-resource-monitor

# Использование ресурсов
docker stats k8s-resource-monitor
```

### Отладка

```bash
# Вход в контейнер
docker-compose exec k8s-resource-monitor bash

# Проверка подключения к K8s
docker-compose exec k8s-resource-monitor kubectl get nodes

# Проверка подключения к Prometheus
docker-compose exec k8s-resource-monitor curl -I http://your-prometheus-server:9090

# Ручной запуск сбора данных
docker-compose exec k8s-resource-monitor curl -X POST http://localhost:8000/api/collect
```

## Структура проекта

После запуска будут созданы директории:

```
k8s-resource-monitor/
├── data/                    # База данных SQLite
│   └── k8s_metrics.db
├── logs/                    # Логи приложения
├── docker-compose.yml       # Docker Compose конфигурация
├── .env                     # Переменные окружения
└── .env.example            # Шаблон настроек
```

## Решение проблем

### Prometheus недоступен

```bash
# Проверьте URL в .env файле
cat .env | grep PROMETHEUS_URL

# Проверьте доступность Prometheus
curl -I http://your-prometheus-server:9090

# Проверьте логи для ошибок подключения
docker-compose logs k8s-resource-monitor | grep -i prometheus
```

### Проблемы с Kubernetes API

```bash
# Проверьте kubeconfig
kubectl get nodes

# Проверьте права доступа
kubectl auth can-i get pods

# Проверьте логи для ошибок K8s
docker-compose logs k8s-resource-monitor | grep -i kubernetes
```

### База данных заблокирована

```bash
# Остановите приложение
docker-compose stop k8s-resource-monitor

# Удалите файлы блокировки
rm -f data/k8s_metrics.db-wal data/k8s_metrics.db-shm

# Перезапустите
docker-compose start k8s-resource-monitor
```

### Очистка данных

```bash
# Остановка
docker-compose down

# Удаление данных
rm -rf data/ logs/

# Перезапуск
docker-compose up -d
```

## Интеграция с внешними системами

### Nginx Reverse Proxy

Создайте `nginx.conf`:

```nginx
server {
    listen 80;
    server_name k8s-monitor.example.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd Service

Создайте `/etc/systemd/system/k8s-resource-monitor.service`:

```ini
[Unit]
Description=K8s Resource Monitor
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/k8s-resource-monitor
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Активация:

```bash
sudo systemctl enable k8s-resource-monitor
sudo systemctl start k8s-resource-monitor
```

## Безопасность

### Рекомендации

1. **Ограничьте CORS origins:**
   ```bash
   CORS_ORIGINS=https://your-domain.com
   ```

2. **Используйте read-only kubeconfig:**
   ```bash
   kubectl create clusterrolebinding k8s-monitor --clusterrole=view --user=monitor-user
   ```

3. **Настройте firewall:**
   ```bash
   # Разрешить только локальный доступ
   sudo ufw allow from 127.0.0.1 to any port 8000
   ```

4. **Регулярно обновляйте образы:**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

## Мониторинг производительности

### Health Checks

```bash
# Проверка состояния
curl http://localhost:8000/health

# Проверка живости
curl http://localhost:8000/health/liveness

# Проверка готовности
curl http://localhost:8000/health/readiness
```

### Метрики

```bash
# API для получения метрик
curl http://localhost:8000/api/metrics

# Статистика по namespace'ам
curl http://localhost:8000/api/summary

# Данные для графиков
curl http://localhost:8000/api/chart-data
```

### Логи

```bash
# Все логи
docker-compose logs k8s-resource-monitor

# Последние 100 строк
docker-compose logs --tail 100 k8s-resource-monitor

# Фильтр по уровню
docker-compose logs k8s-resource-monitor | grep ERROR

# Следить за новыми логами
docker-compose logs -f k8s-resource-monitor
```