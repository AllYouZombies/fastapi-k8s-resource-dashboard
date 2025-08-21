# Kubernetes Resource Monitor

Система мониторинга и анализа утилизации ресурсов в кластере Kubernetes. Позволяет сравнить заявленные ресурсы (requests/limits) с фактическим потреблением CPU и памяти.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-red.svg)

## 🚀 Быстрый старт

### Требования
- Docker и Docker Compose
- Доступ к Kubernetes кластеру (kubeconfig)
- Доступ к Prometheus серверу

### Установка и запуск

```bash
# 1. Клонирование репозитория
git clone https://github.com/AllYouZombies/fastapi-k8s-resource-dashboard.git
cd fastapi-k8s-resource-dashboard

# 2. Настройка конфигурации
cp .env.example .env
# Отредактируйте .env и укажите ваш Prometheus:
# PROMETHEUS_URL=http://your-prometheus:9090

# 3. Запуск (автоматический скрипт)
./start.sh
```

**Или ручной запуск:**

```bash
# Создание директорий
mkdir -p data logs

# Запуск с Docker Compose
docker-compose up -d

# Проверка логов
docker-compose logs -f
```

### Доступ к приложению

- 🌐 **Основной интерфейс**: http://localhost:8000
- 📊 **Dashboard**: http://localhost:8000/dashboard  
- ❤️ **Health Check**: http://localhost:8000/health

## 📋 Описание

Kubernetes Resource Monitor - это веб-приложение для мониторинга и анализа использования ресурсов в Kubernetes кластере. Система собирает данные о заявленных ресурсах (CPU/Memory requests и limits) из Kubernetes API и сравнивает их с фактическим потреблением, получаемым из Prometheus.

### Основные возможности

- 📊 **Мониторинг ресурсов** - Отслеживание CPU и памяти всех подов и контейнеров
- 📈 **Интерактивные дашборды** - 4 специализированные таблицы с данными о ресурсах
- 🔍 **Поиск и фильтрация** - Поиск по имени пода, фильтрация по namespace
- 📱 **Адаптивный интерфейс** - Работает на всех устройствах
- ⏱️ **Автоматический сбор** - Данные обновляются каждые 5 минут
- 💾 **Хранение истории** - SQLite база данных с настраиваемым периодом хранения
- 📋 **Пагинация** - Таблицы с пагинацией по 20 записей на страницу
- 🔄 **Сортировка** - Сортировка по любому столбцу в таблицах
- 📊 **Графики в реальном времени** - 4 отдельных графика для CPU/Memory requests/limits
- 📊 **Исторические данные** - Отображение min/current/max значений за все время
- 🔧 **Рекомендации ресурсов** - Автоматический расчет оптимальных requests и limits
- 📋 **YAML генерация** - Готовые конфигурации для Kubernetes ресурсов

### Интерфейс пользователя

#### Дашборд включает:

1. **Сводная панель** - Общее количество подов, работающих подов, среднее потребление CPU и памяти
2. **Графики трендов** - 4 отдельных графика показывающих процент утилизации:
   - CPU vs Requests (%) - Утилизация CPU относительно заявленных requests
   - CPU vs Limits (%) - Утилизация CPU относительно установленных limits
   - Memory vs Requests (%) - Утилизация памяти относительно заявленных requests  
   - Memory vs Limits (%) - Утилизация памяти относительно установленных limits
3. **Интерактивные таблицы**:
   - Логичный порядок колонок: Node → Namespace → Pod → Container → Status → Resource Data
   - Отображение исторических данных в формате: `min current max` для actual и utilization
   - Кнопки рекомендаций в каждой строке для получения оптимальных настроек ресурсов

#### Возможности таблиц:
- Поиск по имени пода
- Фильтрация по namespace  
- Фильтр "Hide incomplete records" (включен по умолчанию) - скрывает записи без requests/limits
- Сортировка по любому столбцу (по возрастанию/убыванию)
- Пагинация с настраиваемым количеством записей на страницу
- Цветовая индикация статуса подов
- Исторический контекст: min/current/max значения за все время
- AJAX обновления без перезагрузки страницы

#### Рекомендации ресурсов:
- **Requests** основываются на текущем потреблении с правильным округлением
- **Limits** рассчитываются на базе максимального исторического потребления с 25% запасом
- Автоматическая генерация YAML конфигураций для применения в Kubernetes
- Учет полного жизненного цикла пода для точного планирования ресурсов

## 🛠️ Технические особенности

### Архитектура
- **Backend**: FastAPI (асинхронный Python веб-фреймворк)
- **Frontend**: Bootstrap 5 + Chart.js + DataTables
- **База данных**: SQLite с оптимизированными индексами
- **Сбор данных**: Kubernetes API + Prometheus API
- **Фоновые задачи**: APScheduler

### Сбор данных
- **Kubernetes API**: Получение информации о requests/limits всех подов
- **Prometheus**: Сбор фактических метрик потребления CPU и памяти
- **Частота сбора**: Каждые 5 минут (настраивается)
- **Хранение**: SQLite с автоматической ротацией данных

### Безопасность
- Минимальные RBAC права (только чтение подов и ресурсов)
- Запуск от непривилегированного пользователя
- Изоляция в контейнере
- Валидация входных данных

## ⚙️ Настройка окружения

**Обязательные настройки в `.env` файле:**

```bash
# URL вашего Prometheus сервера (ОБЯЗАТЕЛЬНО!)
PROMETHEUS_URL=http://your-prometheus:9090

# Путь к kubeconfig (по умолчанию ~/.kube/config)
KUBECONFIG_PATH=~/.kube/config

# UID/GID пользователя хоста (автоматически устанавливается start.sh)
HOST_UID=1000
HOST_GID=1000
```

**Примеры для разных окружений:**

```bash
# Локальный Prometheus
PROMETHEUS_URL=http://localhost:9090

# Prometheus в Kubernetes
PROMETHEUS_URL=http://kube-prometheus-stack-prometheus.monitoring.svc:9090

# Внешний Prometheus
PROMETHEUS_URL=https://prometheus.company.com

# Port-forward к Prometheus
PROMETHEUS_URL=http://host.docker.internal:9090
```

### Права доступа к kubeconfig

Контейнер создает пользователя с теми же UID/GID, что и у пользователя хоста, для доступа к kubeconfig файлу. Это настраивается автоматически через build args в Docker Compose:

```yaml
build:
  args:
    HOST_UID: ${HOST_UID:-1000}
    HOST_GID: ${HOST_GID:-1000}
```

Скрипт `start.sh` автоматически определяет ваши UID/GID и добавляет их в `.env` файл.

## 🔧 Управление

### Make команды

```bash
make help       # Показать все доступные команды
make start      # Запуск приложения
make stop       # Остановка приложения
make logs       # Просмотр логов
make restart    # Перезапуск приложения
make clean      # Очистка данных
```

### Docker Compose команды

```bash
docker-compose up -d        # Запуск в фоне
docker-compose logs -f      # Просмотр логов
docker-compose ps           # Статус контейнеров
docker-compose down         # Остановка и удаление
```

## 📡 REST API

Приложение предоставляет REST API для интеграции с другими системами:

- `GET /api/metrics` - Получение метрик с пагинацией и фильтрами
- `GET /api/chart-data` - Данные для графиков (4 отдельных series для CPU/Memory)
- `GET /api/namespaces` - Список доступных namespace'ов
- `GET /api/summary` - Сводка по namespace'ам с фильтрацией
- `GET /api/recommendations/{pod_name}/{container_name}` - Рекомендации ресурсов на основе исторических данных
- `GET /health` - Проверка состояния системы

### API рекомендаций ресурсов

Новый endpoint `/api/recommendations/{pod_name}/{container_name}` возвращает:

```json
{
  "pod_name": "example-pod",
  "container_name": "app",
  "namespace": "default",
  "current_usage": {
    "cpu_millicores": 150,
    "memory_mi": 256
  },
  "historical_stats": {
    "cpu": {"min": 0.05, "max": 0.8, "current": 0.15},
    "memory": {"min": 134217728, "max": 536870912, "current": 268435456}
  },
  "recommendations": {
    "cpu": {
      "request": {"millicores": 200, "cores": 0.2},
      "limit": {"millicores": 1000, "cores": 1.0}
    },
    "memory": {
      "request": {"value": 256, "unit": "Mi"},
      "limit": {"value": 640, "unit": "Mi"}
    },
    "yaml": "resources:\\n  requests:\\n    cpu: \"200m\"\\n    memory: \"256Mi\"\\n  limits:\\n    cpu: \"1000m\"\\n    memory: \"640Mi\""
  }
}
```

Статус системы доступен по адресу: http://localhost:8000/health

## 🚀 Развертывание в Kubernetes

Для развертывания в Kubernetes используйте готовые манифесты:

```bash
kubectl apply -f k8s/
```

Манифесты находятся в папке `k8s/` и включают в себя все необходимые ресурсы (Deployment, Service, RBAC).

## 🤝 Поддержка

Issues: https://github.com/AllYouZombies/fastapi-k8s-resource-dashboard/issues

**MIT License**