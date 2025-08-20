#!/bin/bash

# run-k8s-analysis.sh - Запуск полного анализа ресурсов Kubernetes

echo "🚀 Запуск анализа ресурсов Kubernetes"
echo "======================================"

# Проверяем наличие kubectl
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl не найден. Установите kubectl и настройте доступ к кластеру."
    exit 1
fi

# Проверяем доступ к кластеру
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Нет доступа к кластеру Kubernetes. Проверьте kubeconfig."
    exit 1
fi

echo "✅ Подключение к кластеру успешно"

# Запускаем анализ
echo ""
echo "📊 Запускаем сбор и анализ данных..."
if [[ -f "k8s-final-analyzer.sh" ]]; then
    chmod +x k8s-final-analyzer.sh
    ./k8s-final-analyzer.sh
else
    echo "❌ Файл k8s-final-analyzer.sh не найден!"
    exit 1
fi

# Проверяем создание JSON файла
if [[ ! -f "k8s-resources-data.json" ]]; then
    echo "❌ JSON файл не был создан!"
    exit 1
fi

echo ""
echo "✅ Анализ завершен успешно!"
echo "📁 Создан файл: k8s-resources-data.json"

# Проверяем наличие HTML файла
if [[ -f "k8s-advanced-report.html" ]]; then
    echo "📄 HTML интерфейс: k8s-advanced-report.html"
    echo ""
    echo "🌐 Для просмотра запустите веб-сервер:"
    echo "   python3 -m http.server 8000"
    echo ""
    echo "📱 Затем откройте в браузере:"
    echo "   http://localhost:8000/k8s-advanced-report.html"
    echo ""
    echo "💡 Или используйте другие веб-серверы:"
    echo "   npx serve . -p 8000"
    echo "   php -S localhost:8000"
else
    echo "⚠️  HTML файл не найден. Создайте k8s-advanced-report.html"
fi

echo ""
echo "🎯 Готово! Теперь можно анализировать ресурсы в удобном интерфейсе."