#!/bin/bash

# run_services.sh
# Запускает основные компоненты бота как фоновые сервисы

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}!${NC} $1"
}

start_service() {
    local service_name=$1
    local script_name=$2
    local log_file="$LOG_DIR/${service_name}.log"
    local pid_file="$LOG_DIR/${service_name}.pid"
    local script_path="$SCRIPT_DIR/$script_name"

    # Проверяем, не запущен ли уже сервис
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            print_warning "$service_name уже запущен (PID: $pid)"
            return 1
        else
            print_warning "Найден старый PID файл для $service_name, удаляю..."
            rm "$pid_file"
        fi
    fi

    # Проверяем существование скрипта
    if [ ! -f "$script_path" ]; then
        print_error "Скрипт $script_path не найден!"
        return 1
    fi

    print_status "Запускаю $service_name..."

    # Создаем директорию для логов если не существует
    mkdir -p "$(dirname "$log_file")"

    # Переходим в корневую директорию и запускаем процесс
    cd "$SCRIPT_DIR"
    nohup python3 "$script_name" >> "$log_file" 2>&1 &
    local pid=$!

    # Сохраняем PID
    echo $pid > "$pid_file"

    # Ждем немного чтобы проверить запустился ли процесс
    sleep 2
    if ps -p "$pid" > /dev/null 2>&1; then
        print_success "$service_name запущен (PID: $pid)"
        print_status "Логи: $log_file"
        return 0
    else
        print_error "Не удалось запустить $service_name"
        rm "$pid_file"
        return 1
    fi
}

stop_service() {
    local service_name=$1
    local pid_file="$LOG_DIR/${service_name}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            print_status "Останавливаю $service_name (PID: $pid)..."
            # Сначала мягкий сигнал, затем жесткий через 5 секунд
            kill "$pid"

            # Ждем graceful shutdown
            local count=0
            while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done

            # Если процесс все еще жив, убиваем жестко
            if ps -p "$pid" > /dev/null 2>&1; then
                print_warning "Процесс не ответил на мягкий сигнал, принудительно останавливаю..."
                kill -9 "$pid"
                sleep 1
            fi

            if ps -p "$pid" > /dev/null 2>&1; then
                print_error "Не удалось остановить $service_name"
                return 1
            else
                rm "$pid_file"
                print_success "$service_name остановлен"
                return 0
            fi
        else
            print_warning "$service_name не запущен, но найден PID файл"
            rm "$pid_file"
            return 1
        fi
    else
        print_warning "$service_name не запущен (PID файл не найден)"
        return 1
    fi
}

restart_service() {
    local service_name=$1
    local script_name=$2

    print_status "Перезапускаю $service_name..."
    if stop_service "$service_name"; then
        sleep 2
        start_service "$service_name" "$script_name"
    else
        print_warning "Пытаюсь запустить $service_name..."
        start_service "$service_name" "$script_name"
    fi
}

check_service_status() {
    local service_name=$1
    local pid_file="$LOG_DIR/${service_name}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "${GREEN}●${NC} $service_name: запущен (PID: $pid)"
            # Можно добавить проверку здоровья процесса здесь
            return 0
        else
            echo -e "${RED}●${NC} $service_name: не запущен (битый PID файл)"
            return 1
        fi
    else
        echo -e "${RED}●${NC} $service_name: не запущен"
        return 1
    fi
}

show_logs() {
    local service_name=$1
    local log_file="$LOG_DIR/${service_name}.log"
    local lines=${2:-50}  # По умолчанию последние 50 строк

    if [ -f "$log_file" ]; then
        print_status "Последние $lines строк логов $service_name:"
        echo "----------------------------------------"
        tail -n "$lines" "$log_file"
        echo "----------------------------------------"
    else
        print_error "Лог файл $log_file не найден"
    fi
}

case "$1" in
    start)
        print_status "Запуск всех сервисов бота..."
        echo "========================================"

        # Запускаем основной бот
        start_service "telegram_bot_AffilMeetBot" "main.py"

        # Запускаем сервис синхронизации с Google Sheets
        start_service "google_sheets_sync_AffilMeetBot" "main2.py"

        echo "========================================"
        print_success "Все сервисы запущены"
        ;;

    stop)
        print_status "Остановка всех сервисов бота..."
        echo "========================================"

        stop_service "google_sheets_sync_AffilMeetBot"
        stop_service "telegram_bot_AffilMeetBot"

        echo "========================================"
        print_success "Все сервисы остановлены"
        ;;

    restart)
        print_status "Перезапуск всех сервисов бота..."
        $0 stop
        sleep 3
        $0 start
        ;;

    status)
        print_status "Статус сервисов бота:"
        echo "========================================"
        check_service_status "telegram_bot_AffilMeetBot"
        check_service_status "google_sheets_sync_AffilMeetBot"
        echo "========================================"
        ;;

    logs)
        case "$2" in
            bot)
                show_logs "telegram_bot_AffilMeetBot" "$3"
                ;;
            sync)
                show_logs "google_sheets_sync_AffilMeetBot" "$3"
                ;;
            all)
                show_logs "telegram_bot_AffilMeetBot" "$3"
                echo
                show_logs "google_sheets_sync_AffilMeetBot" "$3"
                ;;
            *)
                echo "Использование: $0 logs {bot|sync|all} [количество_строк]"
                echo "  bot  - логи телеграм бота"
                echo "  sync - логи синхронизации с Google Sheets"
                echo "  all  - все логи"
                echo "  количество_строк - опционально (по умолчанию: 50)"
                ;;
        esac
        ;;

    monitor)
        print_status "Режим мониторинга (Ctrl+C для выхода)..."
        while true; do
            clear
            $0 status
            echo
            print_status "Нажмите Ctrl+C для выхода из мониторинга"
            sleep 5
        done
        ;;

    cleanup)
        print_status "Очистка PID файлов и логов..."
        rm -f "$LOG_DIR"/*.pid
        if [ -d "$LOG_DIR" ]; then
            rm -f "$LOG_DIR"/*.log
            print_success "Логи очищены"
        fi
        print_success "Очистка завершена"
        ;;

    *)
        echo "Управление сервисами телеграм бота"
        echo "========================================"
        echo "Использование: $0 {start|stop|restart|status|logs|monitor|cleanup}"
        echo ""
        echo "Команды:"
        echo "  start     - запуск всех сервисов"
        echo "  stop      - остановка всех сервисов"
        echo "  restart   - перезапуск всех сервисов"
        echo "  status    - статус сервисов"
        echo "  logs      - просмотр логов"
        echo "    logs bot [строк]   - логи бота"
        echo "    logs sync [строк]  - логи синхронизации"
        echo "    logs all [строк]   - все логи"
        echo "  monitor   - режим мониторинга статуса"
        echo "  cleanup   - очистка PID файлов и логов"
        echo ""
        echo "Примеры:"
        echo "  $0 start                    # Запустить все сервисы"
        echo "  $0 logs bot 100            # Показать 100 строк логов бота"
        echo "  $0 monitor                  # Режим мониторинга"
        echo "  $0 restart                  # Перезапустить все сервисы"
        exit 1
        ;;
esac