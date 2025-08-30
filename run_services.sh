#!/bin/bash

# run_services.sh
# Запускает main.py и main2.py как фоновые сервисы с логированием

# Директория для логов
LOG_DIR="./logs"
mkdir -p "$LOG_DIR"


# Функция запуска сервиса
start_service() {
    local service_name=$1
    local script_name=$2
    local log_file="$LOG_DIR/${service_name}.log"

    echo "Запуск $service_name..."
    nohup python3 "$script_name" >> "$log_file" 2>&1 &
    echo $! > "${service_name}.pid"
    echo "PID: $(cat ${service_name}.pid), логи: $log_file"
}

# Функция остановки сервиса
stop_service() {
    local service_name=$1
    local pid_file="${service_name}.pid"

    if [ -f "$pid_file" ]; then
        echo "Остановка $service_name (PID: $(cat $pid_file))..."
        kill -9 $(cat "$pid_file")
        rm "$pid_file"
    else
        echo "$service_name не запущен"
    fi
}

# Основное меню
case "$1" in
    start)
        start_service "telegram_bot" "main.py"
        start_service "sync_service" "main2.py"
        ;;
    stop)
        stop_service "telegram_bot"
        stop_service "sync_service"
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        for service in telegram_bot sync_service; do
            if [ -f "${service}.pid" ]; then
                ps -p $(cat "${service}.pid") >/dev/null 2>&1 && \
                echo "$service работает (PID: $(cat ${service}.pid))" || \
                echo "$service не работает (PID файл есть)"
            else
                echo "$service не запущен"
            fi
        done
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

exit 0