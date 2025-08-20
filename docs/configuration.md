# Настройка и конфигурация

Подробное руководство по настройке Kubernetes Resource Monitor.

## Переменные окружения

Приложение настраивается с помощью переменных окружения. Все параметры являются опциональными и имеют значения по умолчанию.

### Основные настройки

| Переменная | Тип | По умолчанию | Описание |
|------------|-----|---------------|----------|
| `APP_NAME` | строка | `"Kubernetes Resource Monitor"` | Название приложения |
| `DEBUG` | булево | `false` | Режим отладки |
| `LOG_LEVEL` | строка | `"INFO"` | Уровень логирования (DEBUG, INFO, WARNING, ERROR) |

### Настройки Kubernetes

| Переменная | Тип | По умолчанию | Описание |
|------------|-----|---------------|----------|
| `K8S_IN_CLUSTER` | булево | `true` | Запуск внутри кластера K8s |
| `K8S_CONFIG_PATH` | строка | `None` | Путь к kubeconfig файлу |
| `EXCLUDED_NAMESPACES` | список | `["kube-system", "kube-public", "kube-node-lease"]` | Исключаемые namespace'ы |

### Настройки Prometheus

| Переменная | Тип | По умолчанию | Описание |
|------------|-----|---------------|----------|
| `PROMETHEUS_URL` | строка | `"http://kube-prometheus-stack-prometheus.monitoring-system.svc:9090"` | URL Prometheus сервера |
| `PROMETHEUS_TIMEOUT` | целое | `30` | Таймаут запросов в секундах |

### Настройки базы данных

| Переменная | Тип | По умолчанию | Описание |
|------------|-----|---------------|----------|
| `DATABASE_URL` | строка | `"sqlite:///./k8s_metrics.db"` | URL подключения к базе данных |
| `RETENTION_DAYS` | целое | `1` | Период хранения данных в днях |

### Настройки планировщика

| Переменная | Тип | По умолчанию | Описание |
|------------|-----|---------------|----------|
| `COLLECTION_INTERVAL_MINUTES` | целое | `5` | Интервал сбора данных в минутах |
| `ENABLE_SCHEDULER` | булево | `true` | Включение фонового планировщика |

### Настройки API

| Переменная | Тип | По умолчанию | Описание |
|------------|-----|---------------|----------|
| `CORS_ORIGINS` | список | `["*"]` | Разрешенные origins для CORS |
| `PAGE_SIZE` | целое | `20` | Размер страницы по умолчанию |

## Файл конфигурации .env

Создайте файл `.env` в корневой директории проекта:

```bash
# Основные настройки
APP_NAME=Kubernetes Resource Monitor
DEBUG=false
LOG_LEVEL=INFO

# Kubernetes настройки
K8S_IN_CLUSTER=false
K8S_CONFIG_PATH=~/.kube/config
EXCLUDED_NAMESPACES=kube-system,kube-public,kube-node-lease,cattle-system

# Prometheus настройки
PROMETHEUS_URL=http://localhost:9090
PROMETHEUS_TIMEOUT=30

# База данных
DATABASE_URL=sqlite:///./data/k8s_metrics.db
RETENTION_DAYS=7

# Планировщик
COLLECTION_INTERVAL_MINUTES=5
ENABLE_SCHEDULER=true

# API настройки
CORS_ORIGINS=*
PAGE_SIZE=20
```

## Настройка подключения к Kubernetes

### Локальный запуск (вне кластера)

```bash
# Использование kubeconfig файла по умолчанию
K8S_IN_CLUSTER=false
K8S_CONFIG_PATH=~/.kube/config

# Использование альтернативного kubeconfig
K8S_IN_CLUSTER=false
K8S_CONFIG_PATH=/path/to/custom/kubeconfig
```

### Запуск внутри кластера

```bash
# Использование Service Account
K8S_IN_CLUSTER=true
```

Убедитесь, что Service Account имеет необходимые права:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: pod-resource-reader
rules:
- apiGroups: [""]
  resources: ["pods", "nodes", "namespaces"]
  verbs: ["get", "list", "watch"]
```

## Настройка Prometheus

### Стандартные запросы

Приложение использует следующие PromQL запросы:

#### CPU Usage

```promql
sum(rate(container_cpu_usage_seconds_total{container!="POD",container!=""}[5m])) by (namespace, pod)
```

#### Memory Usage

```promql
sum(container_memory_working_set_bytes{container!="POD",container!=""}) by (namespace, pod)
```

### Кастомные запросы

Если вы используете другие метрики или labels, отредактируйте файл `app/services/prometheus_service.py`:

```python
async def get_pod_cpu_usage(self) -> Dict[str, float]:
    """Get CPU usage by pod."""
    query = '''
    sum(rate(your_custom_cpu_metric[5m])) by (namespace, pod)
    '''
    # ... остальной код
```

### Настройка URL Prometheus

Для различных установок Prometheus:

#### kube-prometheus-stack

```bash
PROMETHEUS_URL=http://kube-prometheus-stack-prometheus.monitoring.svc:9090
```

#### Prometheus Operator

```bash
PROMETHEUS_URL=http://prometheus-operated.monitoring.svc:9090
```

#### Внешний Prometheus

```bash
PROMETHEUS_URL=http://prometheus.example.com:9090
```

#### Prometheus с аутентификацией

Для Prometheus с базовой аутентификацией измените код в `prometheus_service.py`:

```python
async def __aenter__(self):
    auth = aiohttp.BasicAuth('username', 'password')
    self.session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=self.settings.prometheus_timeout),
        connector=aiohttp.TCPConnector(limit=10),
        auth=auth
    )
    return self
```

## Настройка базы данных

### SQLite (по умолчанию)

```bash
DATABASE_URL=sqlite:///./data/k8s_metrics.db
```

### PostgreSQL

```bash
pip install asyncpg psycopg2-binary

DATABASE_URL=postgresql://user:password@localhost:5432/k8s_metrics
```

Обновите `requirements.txt`:

```text
asyncpg==0.29.0
psycopg2-binary==2.9.9
```

### MySQL

```bash
pip install aiomysql

DATABASE_URL=mysql://user:password@localhost:3306/k8s_metrics
```

## Настройка логирования

### Уровни логирования

- `DEBUG` - Подробная информация для отладки
- `INFO` - Общая информация о работе приложения
- `WARNING` - Предупреждения о потенциальных проблемах
- `ERROR` - Ошибки, не приводящие к остановке приложения
- `CRITICAL` - Критические ошибки

### Настройка формата логов

Создайте файл `logging_config.yaml`:

```yaml
version: 1
disable_existing_loggers: false

formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  detailed:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
  json:
    format: '{"timestamp": "%(asctime)s", "logger": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: default
    stream: ext://sys.stdout

  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: detailed
    filename: /app/logs/app.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

  error_file:
    class: logging.handlers.RotatingFileHandler
    level: ERROR
    formatter: json
    filename: /app/logs/error.log
    maxBytes: 10485760  # 10MB
    backupCount: 3

loggers:
  app:
    level: INFO
    handlers: [console, file, error_file]
    propagate: no

  sqlalchemy:
    level: WARNING
    handlers: [file]
    propagate: no

  kubernetes:
    level: INFO
    handlers: [file]
    propagate: no

root:
  level: INFO
  handlers: [console]
```

## Настройка сбора данных

### Интервал сбора

```bash
# Сбор каждые 5 минут (по умолчанию)
COLLECTION_INTERVAL_MINUTES=5

# Сбор каждую минуту (высокая частота)
COLLECTION_INTERVAL_MINUTES=1

# Сбор каждые 15 минут (низкая частота)
COLLECTION_INTERVAL_MINUTES=15
```

### Период хранения данных

```bash
# Хранение данных 1 день (по умолчанию)
RETENTION_DAYS=1

# Хранение данных 1 неделю
RETENTION_DAYS=7

# Хранение данных 1 месяц
RETENTION_DAYS=30
```

### Исключение namespace'ов

```bash
# Исключение системных namespace'ов
EXCLUDED_NAMESPACES=kube-system,kube-public,kube-node-lease

# Исключение дополнительных namespace'ов
EXCLUDED_NAMESPACES=kube-system,kube-public,kube-node-lease,cattle-system,longhorn-system,monitoring

# Без исключений (собирать данные из всех namespace'ов)
EXCLUDED_NAMESPACES=
```

## Оптимизация производительности

### Настройки базы данных

Для SQLite:

```python
# В database.py
engine = create_engine(
    settings.database_url,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,
        "isolation_level": None  # autocommit mode
    },
    pool_pre_ping=True,
    echo=settings.debug
)
```

### Настройки HTTP клиентов

```python
# В prometheus_service.py
self.session = aiohttp.ClientSession(
    timeout=aiohttp.ClientTimeout(total=30),
    connector=aiohttp.TCPConnector(
        limit=100,  # общий пул соединений
        limit_per_host=30,  # соединений на хост
        keepalive_timeout=30,
        enable_cleanup_closed=True
    )
)
```

### Настройки планировщика

```python
# В scheduler.py
scheduler = AsyncIOScheduler(
    job_defaults={
        'coalesce': True,  # объединение пропущенных задач
        'max_instances': 1,  # предотвращение перекрытий
        'misfire_grace_time': 300  # 5 минут на восстановление
    }
)
```

## Настройка безопасности

### CORS настройки

```bash
# Разрешить все origins (разработка)
CORS_ORIGINS=*

# Разрешить конкретные domains
CORS_ORIGINS=https://monitoring.company.com,https://k8s.company.com

# Разрешить localhost для разработки
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Ограничение доступа к API

Добавьте аутентификацию в `main.py`:

```python
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

security = HTTPBasic()

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "secret")
    if not (correct_username and correct_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return credentials

# Защита API эндпоинтов
app.include_router(api.router, prefix="/api", tags=["API"], dependencies=[Depends(authenticate)])
```

## Примеры конфигураций

### Разработка

```bash
DEBUG=true
LOG_LEVEL=DEBUG
K8S_IN_CLUSTER=false
K8S_CONFIG_PATH=~/.kube/config
PROMETHEUS_URL=http://localhost:9090
COLLECTION_INTERVAL_MINUTES=1
RETENTION_DAYS=1
CORS_ORIGINS=*
```

### Тестирование

```bash
DEBUG=false
LOG_LEVEL=INFO
K8S_IN_CLUSTER=true
PROMETHEUS_URL=http://prometheus.monitoring.svc:9090
COLLECTION_INTERVAL_MINUTES=5
RETENTION_DAYS=3
CORS_ORIGINS=https://test-monitoring.company.com
```

### Продуктив

```bash
DEBUG=false
LOG_LEVEL=WARNING
K8S_IN_CLUSTER=true
PROMETHEUS_URL=http://kube-prometheus-stack-prometheus.monitoring.svc:9090
COLLECTION_INTERVAL_MINUTES=5
RETENTION_DAYS=7
EXCLUDED_NAMESPACES=kube-system,kube-public,kube-node-lease,cattle-system
CORS_ORIGINS=https://monitoring.company.com
PAGE_SIZE=50
```