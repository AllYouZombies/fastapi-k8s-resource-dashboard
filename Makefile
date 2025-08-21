.PHONY: help start stop restart logs build clean setup dev test lint

# Переменные
COMPOSE_FILE=compose.yml
CONTAINER_NAME=k8s-resource-monitor

# Цвета для вывода
GREEN=\033[0;32m
YELLOW=\033[1;33m
RED=\033[0;31m
NC=\033[0m

help: ## Показать это сообщение помощи
	@echo "$(GREEN)Kubernetes Resource Monitor - Команды разработки$(NC)"
	@echo "=================================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

setup: ## Первоначальная настройка проекта
	@echo "$(GREEN)Настройка проекта...$(NC)"
	@if [ ! -f .env ]; then cp .env.example .env && echo "$(YELLOW)Создан .env файл. Настройте PROMETHEUS_URL!$(NC)"; fi
	@mkdir -p data logs
	@echo "$(GREEN)✓ Настройка завершена$(NC)"

start: setup ## Запуск приложения с Docker Compose
	@echo "$(GREEN)Запуск приложения...$(NC)"
	@if command -v docker-compose >/dev/null 2>&1; then docker-compose -f $(COMPOSE_FILE) up -d; else docker compose -f $(COMPOSE_FILE) up -d; fi
	@echo "$(GREEN)✓ Приложение запущено: http://localhost:8000$(NC)"

stop: ## Остановка приложения
	@echo "$(YELLOW)Остановка приложения...$(NC)"
	@if command -v docker-compose >/dev/null 2>&1; then docker-compose -f $(COMPOSE_FILE) down; else docker compose -f $(COMPOSE_FILE) down; fi
	@echo "$(GREEN)✓ Приложение остановлено$(NC)"

restart: ## Перезапуск приложения
	@echo "$(YELLOW)Перезапуск приложения...$(NC)"
	@if command -v docker-compose >/dev/null 2>&1; then docker-compose -f $(COMPOSE_FILE) restart; else docker compose -f $(COMPOSE_FILE) restart; fi
	@echo "$(GREEN)✓ Приложение перезапущено$(NC)"

logs: ## Просмотр логов
	@if command -v docker-compose >/dev/null 2>&1; then docker-compose -f $(COMPOSE_FILE) logs -f $(CONTAINER_NAME); else docker compose -f $(COMPOSE_FILE) logs -f $(CONTAINER_NAME); fi

build: ## Сборка Docker образа
	@echo "$(GREEN)Сборка образа...$(NC)"
	@if command -v docker-compose >/dev/null 2>&1; then docker-compose -f $(COMPOSE_FILE) build --no-cache; else docker compose -f $(COMPOSE_FILE) build --no-cache; fi
	@echo "$(GREEN)✓ Образ собран$(NC)"

rebuild: build start ## Пересборка и запуск

status: ## Статус контейнеров
	@if command -v docker-compose >/dev/null 2>&1; then docker-compose -f $(COMPOSE_FILE) ps; else docker compose -f $(COMPOSE_FILE) ps; fi

shell: ## Вход в контейнер
	@if command -v docker-compose >/dev/null 2>&1; then docker-compose -f $(COMPOSE_FILE) exec $(CONTAINER_NAME) bash; else docker compose -f $(COMPOSE_FILE) exec $(CONTAINER_NAME) bash; fi

dev: ## Запуск в режиме разработки (локально)
	@echo "$(GREEN)Запуск в режиме разработки...$(NC)"
	@pip install -r requirements.txt
	@uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test: ## Запуск тестов (если есть)
	@echo "$(GREEN)Запуск тестов...$(NC)"
	@pytest tests/ -v

lint: ## Проверка кода
	@echo "$(GREEN)Проверка кода...$(NC)"
	@flake8 app/ --max-line-length=100
	@black app/ --check
	@isort app/ --check-only

format: ## Форматирование кода
	@echo "$(GREEN)Форматирование кода...$(NC)"
	@black app/
	@isort app/

clean: ## Очистка данных и логов
	@echo "$(YELLOW)Очистка данных...$(NC)"
	@rm -rf data/* logs/*
	@echo "$(GREEN)✓ Данные очищены$(NC)"

clean-all: stop clean ## Полная очистка (остановка + очистка данных)
	@if command -v docker-compose >/dev/null 2>&1; then docker-compose -f $(COMPOSE_FILE) down -v; else docker compose -f $(COMPOSE_FILE) down -v; fi
	@docker system prune -f
	@echo "$(GREEN)✓ Полная очистка завершена$(NC)"

health: ## Проверка здоровья приложения
	@echo "$(GREEN)Проверка здоровья...$(NC)"
	@curl -s http://localhost:8000/health | jq . || echo "$(RED)Приложение недоступно$(NC)"

auto-start: ## Автоматический запуск со скриптом
	@./start.sh

# Kubernetes команды
k8s-deploy: ## Развертывание в Kubernetes
	@echo "$(GREEN)Развертывание в Kubernetes...$(NC)"
	@kubectl apply -f k8s/namespace.yaml
	@kubectl apply -f k8s/rbac.yaml
	@kubectl apply -f k8s/deployment.yaml
	@kubectl apply -f k8s/service.yaml
	@echo "$(GREEN)✓ Развернуто в Kubernetes$(NC)"

k8s-logs: ## Логи из Kubernetes
	@kubectl logs -f deployment/k8s-resource-monitor -n monitoring

k8s-status: ## Статус в Kubernetes
	@kubectl get all -n monitoring -l app=k8s-resource-monitor

k8s-delete: ## Удаление из Kubernetes
	@kubectl delete -f k8s/

# Утилиты
check-deps: ## Проверка зависимостей
	@echo "$(GREEN)Проверка зависимостей...$(NC)"
	@command -v docker >/dev/null 2>&1 || { echo "$(RED)Docker не установлен$(NC)"; exit 1; }
	@(command -v docker-compose >/dev/null 2>&1 || docker compose version >/dev/null 2>&1) || { echo "$(RED)Docker Compose не установлен$(NC)"; exit 1; }
	@command -v kubectl >/dev/null 2>&1 || echo "$(YELLOW)kubectl не найден$(NC)"
	@echo "$(GREEN)✓ Основные зависимости проверены$(NC)"

install: check-deps setup start ## Полная установка и запуск

# По умолчанию показываем help
.DEFAULT_GOAL := help