# Kubernetes Resource Monitor

Система мониторинга и анализа утилизации ресурсов в кластере Kubernetes. Позволяет сравнить заявленные ресурсы (requests/limits) с фактическим потреблением CPU и памяти.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-red.svg)

## 📸 Интерфейс системы

<table>
<tr>
<td width="50%" align="center">
<img src="docs/media/screenshot-03.png" alt="Resource Recommendations" width="100%">
<br><em>Система рекомендаций ресурсов с автоматической генерацией YAML</em>
</td>
<td width="50%">
<img src="docs/media/screenshot-01.png" alt="Dashboard Overview" width="100%">
<br><em>Основной дашборд с метриками и сводными данными</em>
<br><br>
<img src="docs/media/screenshot-02.png" alt="Resource Tables" width="100%">
<br><em>Интерактивные таблицы с данными о ресурсах и историей потребления</em>
</td>
</tr>
</table>

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

## 📋 Возможности

- 📊 **Мониторинг ресурсов** - CPU и память всех подов с историческими данными (min/current/max)
- 📈 **Интерактивные таблицы** - 4 специализированные таблицы с поиском, фильтрацией и сортировкой
- 📊 **Графики в реальном времени** - Отслеживание процентов утилизации CPU/Memory vs requests/limits
- 🔧 **Умные рекомендации** - Автоматический расчет оптимальных requests/limits с генерацией YAML
- ⏱️ **Автоматический сбор** - Обновление данных каждые 5 минут из Kubernetes API и Prometheus
- 🔍 **Продвинутые фильтры** - По namespace, неполным данным, с исключением системных namespace'ов

### Интерфейс

**Дашборд содержит:**
- Сводная панель с метриками кластера
- 4 интерактивных графика утилизации (CPU/Memory vs Requests/Limits)
- 4 таблицы ресурсов с поиском, фильтрацией и сортировкой
- Кнопки рекомендаций в каждой строке таблиц

**Система рекомендаций:**
- Requests основываются на текущем потреблении
- Limits рассчитываются по максимальному потреблению + 25% запас
- Автоматическая генерация готовых YAML конфигураций

## 🛠️ Технические особенности

**Стек технологий:**
- FastAPI (асинхронный Python)
- Bootstrap 5 + Chart.js + DataTables
- SQLite с оптимизированными индексами
- Kubernetes API + Prometheus API

**Безопасность:**
- Минимальные RBAC права (read-only)
- Непривилегированный пользователь в контейнере
- Исключение системных namespace'ов (kube-system, etc.)

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

**Основные endpoints:**
- `GET /api/metrics` - Метрики с пагинацией и фильтрами
- `GET /api/chart-data` - Данные для графиков
- `GET /api/recommendations/{pod_name}/{container_name}` - Рекомендации ресурсов
- `GET /health` - Состояние системы

## 🚀 Развертывание в Kubernetes

Для развертывания в Kubernetes используйте готовые манифесты:

```bash
kubectl apply -f k8s/
```

Манифесты находятся в папке `k8s/` и включают в себя все необходимые ресурсы (Deployment, Service, RBAC).

## 🤝 Поддержка

Issues: https://github.com/AllYouZombies/fastapi-k8s-resource-dashboard/issues

**MIT License**