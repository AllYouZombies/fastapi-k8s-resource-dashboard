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
- 🔧 **API документация**: http://localhost:8000/docs
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
- 📊 **Графики в реальном времени** - Визуализация трендов потребления ресурсов

### Интерфейс пользователя

#### Дашборд включает:

1. **Сводная панель** - Общее количество подов, работающих подов, среднее потребление CPU и памяти
2. **Графики трендов** - CPU и Memory Utilization за последние часы  
3. **Интерактивные таблицы**:
   - CPU Requests vs Usage - Сравнение заявленных CPU requests с фактическим использованием
   - CPU Limits vs Usage - Сравнение CPU limits с фактическим использованием  
   - Memory Requests vs Usage - Сравнение заявленных Memory requests с фактическим использованием
   - Memory Limits vs Usage - Сравнение Memory limits с фактическим использованием

#### Возможности таблиц:
- Поиск по имени пода
- Фильтрация по namespace
- Сортировка по любому столбцу (по возрастанию/убыванию)
- Пагинация с настраиваемым количеством записей на страницу
- Цветовая индикация статуса подов
- Выделение высокого потребления ресурсов

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

Все остальные настройки имеют разумные значения по умолчанию.

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
- `GET /api/chart-data` - Данные для графиков
- `GET /api/namespaces` - Список доступных namespace'ов
- `GET /api/summary` - Сводка по namespace'ам
- `GET /health` - Проверка состояния системы

Документация API доступна по адресу: http://localhost:8000/docs

## 🚀 Развертывание в Kubernetes

Для развертывания в Kubernetes используйте готовые манифесты:

```bash
kubectl apply -f k8s/
```

Манифесты находятся в папке `k8s/` и включают в себя все необходимые ресурсы (Deployment, Service, RBAC).

## 🤝 Поддержка

Issues: https://github.com/AllYouZombies/fastapi-k8s-resource-dashboard/issues

**MIT License**