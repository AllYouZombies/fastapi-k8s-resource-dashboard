# 📁 Структура проекта

```
k8s-resource-monitor/
├── README.md                   # Главное описание проекта
├── start.sh                    # Автоматический скрипт запуска
├── docker-compose.yml          # Docker Compose конфигурация
├── Makefile                    # Команды разработки
├── requirements.txt            # Python зависимости
├── .env.example               # Шаблон конфигурации
│
├── app/                       # Исходный код приложения
│   ├── main.py               # FastAPI точка входа
│   ├── core/                 # Основные компоненты
│   │   ├── config.py        # Конфигурация
│   │   ├── database.py      # База данных
│   │   ├── dependencies.py  # Dependency injection
│   │   └── scheduler.py     # Фоновые задачи
│   ├── models/              # Модели данных
│   │   ├── database.py      # SQLAlchemy модели
│   │   └── schemas.py       # Pydantic схемы
│   ├── services/            # Бизнес-логика
│   │   ├── kubernetes_service.py    # Работа с K8s API
│   │   ├── prometheus_service.py    # Работа с Prometheus
│   │   └── collector_service.py     # Сбор метрик
│   ├── api/                 # API роутеры
│   │   └── routes/
│   │       ├── dashboard.py # Веб-интерфейс
│   │       ├── api.py      # REST API
│   │       └── health.py   # Health checks
│   └── static/             # Статические файлы
│       ├── css/
│       ├── js/
│       └── templates/
│
├── docker/                   # Docker конфигурация
│   └── Dockerfile           # Образ приложения
│
├── k8s/                     # Kubernetes манифесты
│   ├── namespace.yaml
│   ├── rbac.yaml
│   ├── deployment.yaml
│   └── service.yaml
│
└── docs/                    # Документация
    ├── INDEX.md            # Оглавление документации
    ├── QUICKSTART.md       # Быстрый старт
    ├── README.docker-compose.md   # Docker Compose
    ├── docker-deployment.md       # Docker развертывание
    ├── kubernetes-deployment.md   # Kubernetes развертывание
    ├── configuration.md           # Настройка
    ├── operations.md             # Администрирование
    ├── PRODUCTION-READY.md       # Готовность к продуктиву
    └── CLAUDE.md                 # Руководство для ИИ
```

## 📂 Автоматически создаваемые директории

При запуске создаются:

```
├── data/                    # База данных SQLite
│   └── k8s_metrics.db
├── logs/                    # Логи приложения
└── .env                     # Локальная конфигурация (из .env.example)
```

## 🎯 Ключевые файлы для запуска

### Обязательные для работы:
- `start.sh` - автоматический запуск
- `docker-compose.yml` - контейнеризация
- `.env.example` - шаблон настроек
- `app/` - исходный код
- `requirements.txt` - зависимости

### Для разработки:
- `Makefile` - команды разработки
- `docs/` - документация
- `k8s/` - манифесты Kubernetes

### Служебные:
- `.gitignore`, `.dockerignore` - исключения
- `docker/Dockerfile` - образ приложения