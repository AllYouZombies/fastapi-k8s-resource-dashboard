#!/bin/bash

# k8s-final-analyzer.sh - Финальная версия анализатора ресурсов Kubernetes
set -e

echo "=== Анализ ресурсов Kubernetes ==="

# Создаем временную директорию
TEMP_DIR=$(mktemp -d)
JSON_FILE="k8s-resources-data.json"

# Функция очистки
cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# Функции конвертации
cpu_to_mc() {
    local val="$1"
    if [[ "$val" == *"m" ]]; then
        echo "${val%m}"
    elif [[ "$val" =~ ^[0-9]*\.?[0-9]+$ ]]; then
        echo $(awk "BEGIN {print int($val * 1000)}")
    else
        echo "0"
    fi
}

mem_to_mi() {
    local val="$1"
    if [[ "$val" == *"Gi" ]]; then
        echo $(awk "BEGIN {print int(${val%Gi} * 1024)}")
    elif [[ "$val" == *"Mi" ]]; then
        echo "${val%Mi}"
    elif [[ "$val" == *"Ki" ]]; then
        echo $(awk "BEGIN {print int(${val%Ki} / 1024)}")
    else
        echo "0"
    fi
}

calc_percent() {
    local usage="$1"
    local request="$2"
    if [[ $request -gt 0 && $usage -gt 0 ]]; then
        echo $(awk "BEGIN {print int($usage * 100 / $request)}")
    else
        echo "0"
    fi
}

echo "1. Получаем данные о подах и контейнерах..."

# Получаем данные о ресурсах подов
kubectl get pods --all-namespaces -o json | jq -r '
.items[] |
select(.status.phase == "Running" and .metadata.namespace != "kube-system") |
.spec.containers[] as $container |
select(
    ($container.resources.requests.cpu // "") != "" or
    ($container.resources.requests.memory // "") != "" or
    ($container.resources.limits.cpu // "") != "" or
    ($container.resources.limits.memory // "") != ""
) |
[
    .metadata.namespace,
    .metadata.name,
    $container.name,
    ($container.resources.requests.cpu // "0"),
    ($container.resources.requests.memory // "0"),
    ($container.resources.limits.cpu // "0"),
    ($container.resources.limits.memory // "0")
] | @tsv' > "$TEMP_DIR/pods.tsv"

echo "2. Получаем данные об использовании ресурсов..."

# Получаем данные об использовании
kubectl top pods --all-namespaces 2>/dev/null | grep -v kube-system | tail -n +2 > "$TEMP_DIR/usage.txt" 2>/dev/null || echo "No usage data" > "$TEMP_DIR/usage.txt"

echo "3. Создаем JSON файл с полными данными..."

# Создаем начало JSON файла построчно
echo '{' > "$JSON_FILE"
echo '  "metadata": {' >> "$JSON_FILE"
echo '    "generated_at": "",' >> "$JSON_FILE"
echo '    "cluster_info": {' >> "$JSON_FILE"
echo '      "total_containers": 0,' >> "$JSON_FILE"
echo '      "total_pods": 0' >> "$JSON_FILE"
echo '    },' >> "$JSON_FILE"
echo '    "analysis_summary": {' >> "$JSON_FILE"
echo '      "requests": {' >> "$JSON_FILE"
echo '        "overuse_cpu": 0,' >> "$JSON_FILE"
echo '        "overuse_memory": 0,' >> "$JSON_FILE"
echo '        "underuse_cpu": 0,' >> "$JSON_FILE"
echo '        "underuse_memory": 0,' >> "$JSON_FILE"
echo '        "potential_cpu_savings_cores": 0,' >> "$JSON_FILE"
echo '        "potential_memory_savings_gi": 0' >> "$JSON_FILE"
echo '      },' >> "$JSON_FILE"
echo '      "limits": {' >> "$JSON_FILE"
echo '        "overuse_cpu": 0,' >> "$JSON_FILE"
echo '        "overuse_memory": 0,' >> "$JSON_FILE"
echo '        "underuse_cpu": 0,' >> "$JSON_FILE"
echo '        "underuse_memory": 0' >> "$JSON_FILE"
echo '      }' >> "$JSON_FILE"
echo '    }' >> "$JSON_FILE"
echo '  },' >> "$JSON_FILE"
echo '  "containers": [' >> "$JSON_FILE"

# Счетчики для анализа
total_containers=0
unique_pods=()
requests_cpu_overuse=0
requests_mem_overuse=0
requests_cpu_underuse=0
requests_mem_underuse=0
limits_cpu_overuse=0
limits_mem_overuse=0
limits_cpu_underuse=0
limits_mem_underuse=0
potential_cpu_savings=0
potential_mem_savings=0

# Читаем данные об использовании в ассоциативный массив
declare -A usage_map
while read -r line; do
    if [[ -n "$line" && "$line" != "No usage data" ]]; then
        ns=$(echo "$line" | awk '{print $1}')
        pod=$(echo "$line" | awk '{print $2}')
        cpu=$(echo "$line" | awk '{print $3}')
        mem=$(echo "$line" | awk '{print $4}')
        usage_map["${ns}/${pod}"]="${cpu}|${mem}"
    fi
done < "$TEMP_DIR/usage.txt"

first_entry=true

# Обрабатываем каждый контейнер
while IFS=$'\t' read -r namespace pod container cpu_req mem_req cpu_lim mem_lim; do

    # Добавляем уникальные поды
    pod_key="${namespace}/${pod}"
    if [[ ! " ${unique_pods[@]} " =~ " ${pod_key} " ]]; then
        unique_pods+=("$pod_key")
    fi

    # Получаем данные об использовании
    if [[ -n "${usage_map[$pod_key]}" ]]; then
        IFS='|' read -r cpu_usage mem_usage <<< "${usage_map[$pod_key]}"
    else
        cpu_usage="N/A"
        mem_usage="N/A"
    fi

    # Конвертируем в числа
    cpu_req_mc=$(cpu_to_mc "$cpu_req")
    cpu_lim_mc=$(cpu_to_mc "$cpu_lim")
    mem_req_mi=$(mem_to_mi "$mem_req")
    mem_lim_mi=$(mem_to_mi "$mem_lim")

    cpu_usage_mc=0
    mem_usage_mi=0
    if [[ "$cpu_usage" != "N/A" ]]; then
        cpu_usage_mc=$(cpu_to_mc "$cpu_usage")
    fi
    if [[ "$mem_usage" != "N/A" ]]; then
        mem_usage_mi=$(mem_to_mi "$mem_usage")
    fi

    # Рассчитываем проценты для requests
    cpu_req_eff=$(calc_percent "$cpu_usage_mc" "$cpu_req_mc")
    mem_req_eff=$(calc_percent "$mem_usage_mi" "$mem_req_mi")

    # Рассчитываем проценты для limits
    cpu_lim_eff=$(calc_percent "$cpu_usage_mc" "$cpu_lim_mc")
    mem_lim_eff=$(calc_percent "$mem_usage_mi" "$mem_lim_mi")

    # Анализируем requests
    if [[ $cpu_req_eff -gt 100 ]]; then
        requests_cpu_overuse=$((requests_cpu_overuse + 1))
    elif [[ $cpu_req_eff -lt 20 && $cpu_req_mc -gt 50 ]]; then
        requests_cpu_underuse=$((requests_cpu_underuse + 1))
        # Потенциальная экономия CPU (80% от текущих requests)
        savings=$(awk "BEGIN {print int($cpu_req_mc * 0.8)}")
        potential_cpu_savings=$((potential_cpu_savings + savings))
    fi

    if [[ $mem_req_eff -gt 100 ]]; then
        requests_mem_overuse=$((requests_mem_overuse + 1))
    elif [[ $mem_req_eff -lt 50 && $mem_req_mi -gt 100 ]]; then
        requests_mem_underuse=$((requests_mem_underuse + 1))
        # Потенциальная экономия Memory (50% от текущих requests)
        savings=$(awk "BEGIN {print int($mem_req_mi * 0.5)}")
        potential_mem_savings=$((potential_mem_savings + savings))
    fi

    # Анализируем limits
    if [[ $cpu_lim_eff -gt 80 ]]; then
        limits_cpu_overuse=$((limits_cpu_overuse + 1))
    elif [[ $cpu_lim_eff -lt 10 && $cpu_lim_mc -gt 100 ]]; then
        limits_cpu_underuse=$((limits_cpu_underuse + 1))
    fi

    if [[ $mem_lim_eff -gt 80 ]]; then
        limits_mem_overuse=$((limits_mem_overuse + 1))
    elif [[ $mem_lim_eff -lt 30 && $mem_lim_mi -gt 200 ]]; then
        limits_mem_underuse=$((limits_mem_underuse + 1))
    fi

    # Определяем категории
    req_cpu_category="normal"
    req_mem_category="normal"
    lim_cpu_category="normal"
    lim_mem_category="normal"

    if [[ $cpu_req_eff -gt 100 ]]; then
        req_cpu_category="overuse"
    elif [[ $cpu_req_eff -lt 20 ]]; then
        req_cpu_category="underuse"
    fi

    if [[ $mem_req_eff -gt 100 ]]; then
        req_mem_category="overuse"
    elif [[ $mem_req_eff -lt 50 ]]; then
        req_mem_category="underuse"
    fi

    if [[ $cpu_lim_eff -gt 80 ]]; then
        lim_cpu_category="overuse"
    elif [[ $cpu_lim_eff -lt 10 ]]; then
        lim_cpu_category="underuse"
    fi

    if [[ $mem_lim_eff -gt 80 ]]; then
        lim_mem_category="overuse"
    elif [[ $mem_lim_eff -lt 30 ]]; then
        lim_mem_category="underuse"
    fi

    total_containers=$((total_containers + 1))

    # Форматируем значения
    [[ "$cpu_req" == "0" ]] && cpu_req="-"
    [[ "$cpu_lim" == "0" ]] && cpu_lim="-"
    [[ "$mem_req" == "0" ]] && mem_req="-"
    [[ "$mem_lim" == "0" ]] && mem_lim="-"
    [[ "$cpu_usage" == "N/A" ]] && cpu_usage="-"
    [[ "$mem_usage" == "N/A" ]] && mem_usage="-"

    # Добавляем запятую если не первый элемент
    if [[ "$first_entry" == "false" ]]; then
        echo "," >> "$JSON_FILE"
    fi
    first_entry=false

    # Добавляем JSON объект построчно
    echo '    {' >> "$JSON_FILE"
    echo "      \"namespace\": \"$namespace\"," >> "$JSON_FILE"
    echo "      \"pod\": \"$pod\"," >> "$JSON_FILE"
    echo "      \"container\": \"$container\"," >> "$JSON_FILE"
    echo '      "resources": {' >> "$JSON_FILE"
    echo '        "cpu": {' >> "$JSON_FILE"
    echo "          \"request\": \"$cpu_req\"," >> "$JSON_FILE"
    echo "          \"limit\": \"$cpu_lim\"," >> "$JSON_FILE"
    echo "          \"usage\": \"$cpu_usage\"," >> "$JSON_FILE"
    echo "          \"request_efficiency_percent\": $cpu_req_eff," >> "$JSON_FILE"
    echo "          \"limit_efficiency_percent\": $cpu_lim_eff" >> "$JSON_FILE"
    echo '        },' >> "$JSON_FILE"
    echo '        "memory": {' >> "$JSON_FILE"
    echo "          \"request\": \"$mem_req\"," >> "$JSON_FILE"
    echo "          \"limit\": \"$mem_lim\"," >> "$JSON_FILE"
    echo "          \"usage\": \"$mem_usage\"," >> "$JSON_FILE"
    echo "          \"request_efficiency_percent\": $mem_req_eff," >> "$JSON_FILE"
    echo "          \"limit_efficiency_percent\": $mem_lim_eff" >> "$JSON_FILE"
    echo '        }' >> "$JSON_FILE"
    echo '      },' >> "$JSON_FILE"
    echo '      "analysis": {' >> "$JSON_FILE"
    echo '        "requests": {' >> "$JSON_FILE"
    echo "          \"cpu_category\": \"$req_cpu_category\"," >> "$JSON_FILE"
    echo "          \"memory_category\": \"$req_mem_category\"" >> "$JSON_FILE"
    echo '        },' >> "$JSON_FILE"
    echo '        "limits": {' >> "$JSON_FILE"
    echo "          \"cpu_category\": \"$lim_cpu_category\"," >> "$JSON_FILE"
    echo "          \"memory_category\": \"$lim_mem_category\"" >> "$JSON_FILE"
    echo '        }' >> "$JSON_FILE"
    echo '      }' >> "$JSON_FILE"
    echo -n '    }' >> "$JSON_FILE"

done < "$TEMP_DIR/pods.tsv"

# Завершаем JSON
echo "" >> "$JSON_FILE"
echo "  ]" >> "$JSON_FILE"
echo "}" >> "$JSON_FILE"

# Рассчитываем экономию в ядрах и гигабайтах
potential_cpu_cores=$(awk "BEGIN {printf \"%.1f\", $potential_cpu_savings / 1000}")
potential_mem_gi=$(awk "BEGIN {printf \"%.1f\", $potential_mem_savings / 1024}")

echo "4. Обновляем метаданные в JSON..."

# Обновляем метаданные
current_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
temp_json=$(mktemp)

sed "s/\"generated_at\": \"\"/\"generated_at\": \"$current_date\"/" "$JSON_FILE" | \
jq --arg total_containers "$total_containers" \
   --arg total_pods "${#unique_pods[@]}" \
   --arg req_cpu_over "$requests_cpu_overuse" \
   --arg req_mem_over "$requests_mem_overuse" \
   --arg req_cpu_under "$requests_cpu_underuse" \
   --arg req_mem_under "$requests_mem_underuse" \
   --arg lim_cpu_over "$limits_cpu_overuse" \
   --arg lim_mem_over "$limits_mem_overuse" \
   --arg lim_cpu_under "$limits_cpu_underuse" \
   --arg lim_mem_under "$limits_mem_underuse" \
   --arg cpu_savings "$potential_cpu_cores" \
   --arg mem_savings "$potential_mem_gi" \
   '.metadata.cluster_info.total_containers = ($total_containers | tonumber) |
    .metadata.cluster_info.total_pods = ($total_pods | tonumber) |
    .metadata.analysis_summary.requests.overuse_cpu = ($req_cpu_over | tonumber) |
    .metadata.analysis_summary.requests.overuse_memory = ($req_mem_over | tonumber) |
    .metadata.analysis_summary.requests.underuse_cpu = ($req_cpu_under | tonumber) |
    .metadata.analysis_summary.requests.underuse_memory = ($req_mem_under | tonumber) |
    .metadata.analysis_summary.limits.overuse_cpu = ($lim_cpu_over | tonumber) |
    .metadata.analysis_summary.limits.overuse_memory = ($lim_mem_over | tonumber) |
    .metadata.analysis_summary.limits.underuse_cpu = ($lim_cpu_under | tonumber) |
    .metadata.analysis_summary.limits.underuse_memory = ($lim_mem_under | tonumber) |
    .metadata.analysis_summary.requests.potential_cpu_savings_cores = ($cpu_savings | tonumber) |
    .metadata.analysis_summary.requests.potential_memory_savings_gi = ($mem_savings | tonumber)' > "$temp_json"

mv "$temp_json" "$JSON_FILE"

echo "✅ Анализ завершен!"
echo ""
echo "📊 Результаты:"
echo "- Всего контейнеров: $total_containers"
echo "- Всего подов: ${#unique_pods[@]}"
echo "- Переиспользование CPU requests: $requests_cpu_overuse контейнеров"
echo "- Переиспользование Memory requests: $requests_mem_overuse контейнеров"
echo "- Недоиспользование CPU requests: $requests_cpu_underuse контейнеров"
echo "- Недоиспользование Memory requests: $requests_mem_underuse контейнеров"
echo "- Потенциальная экономия CPU: $potential_cpu_cores ядер"
echo "- Потенциальная экономия Memory: $potential_mem_gi Gi"
echo ""
echo "📁 JSON файл создан: $JSON_FILE"
echo "🚀 Запустите HTML интерфейс для детального анализа"
