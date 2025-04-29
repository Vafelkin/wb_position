from flask import Flask, render_template, request, redirect, url_for, jsonify
import data_manager
import wb_parser
import threading
import time
from urllib.parse import quote_plus

app = Flask(__name__)

# --- Статус фоновой задачи ---
# Используем словарь для хранения состояния и блокировку для потокобезопасности
check_status_lock = threading.Lock()
check_status = {
    "running": False,
    "message": "Ожидание",
    "progress": 0,
    "total": 0
}

def update_status(running=None, message=None, progress=None, total=None):
    """Потокобезопасное обновление статуса проверки."""
    with check_status_lock:
        if running is not None: check_status["running"] = running
        if message is not None: check_status["message"] = message
        if progress is not None: check_status["progress"] = progress
        if total is not None: check_status["total"] = total
        print(f"[Status Update] {check_status}") # Логируем изменение статуса

def background_check_positions():
    """Функция, выполняющая проверку позиций в фоновом потоке."""
    items = data_manager.load_items_to_track()
    total_items = len(items)
    update_status(running=True, message="Подготовка к проверке...", progress=0, total=total_items)

    if not items:
        print("Нет товаров для проверки.")
        update_status(running=False, message="Нет товаров для проверки", progress=0, total=0)
        return

    print("\n--- Запуск фоновой проверки позиций ---")
    for i, item in enumerate(items):
        sku = item['sku']
        query = item['query']
        current_progress = i + 1

        # Получаем максимальное количество страниц из парсера (для отображения)
        max_pages_for_status = wb_parser.MAX_PAGES_TO_CHECK
        def page_update_callback(page_num):
            update_status(message=f"Проверка {current_progress}/{total_items}: SKU {sku}, Запрос '{query}' [Стр. {page_num}/{max_pages_for_status}]", progress=i)

        # Обновляем статус перед началом поиска конкретного SKU
        update_status(message=f"Проверка {current_progress}/{total_items}: SKU {sku}, Запрос '{query}' [Начинаем поиск...]", progress=i)

        print(f"Проверяем: SKU={sku}, Запрос='{query}'")
        try:
            # Передаем callback в парсер
            position_data = wb_parser.get_product_position(sku, query, status_updater=page_update_callback)

            record_data = position_data if position_data else \
                          {'absolute_position': None, 'page': None, 'position_on_page': None}
            data_manager.add_position_record(sku, query, record_data)

            # Обновляем статус после завершения поиска SKU (найден или нет)
            result_message = "Найден" if position_data else "Не найден"
            update_status(message=f"Проверка {current_progress}/{total_items}: SKU {sku}, Запрос '{query}' [{result_message}]", progress=current_progress)
            print("---")
        except Exception as e:
            print(f"ОШИБКА при проверке SKU {sku}, Запрос '{query}': {e}")
            # Можно добавить запись об ошибке в статус или лог
            update_status(message=f"Ошибка при проверке {current_progress}/{total_items}: SKU {sku} ({e})", progress=current_progress) # Показываем ошибку в статусе
            time.sleep(2) # Небольшая пауза после ошибки

    print("--- Фоновая проверка позиций завершена ---")
    update_status(running=False, message="Проверка завершена", progress=total_items)
# ----------------------------

@app.route('/')
def index():
    """Главная страница, отображает список отслеживаемых товаров и историю."""
    items = data_manager.load_items_to_track()
    history = data_manager.load_tracking_data() # Используем снова имя history

    # Добавляем закодированный запрос для ссылок в шаблоне
    for item in items:
        item['encoded_query'] = quote_plus(item['query'])

    # Просто передаем items и history как раньше
    return render_template('index.html', items=items, history=history)

@app.route('/add', methods=['POST'])
def add_item():
    """Добавляет новый товар для отслеживания."""
    sku = request.form.get('sku')
    query = request.form.get('query')
    if sku and query:
        # Простая валидация SKU (должен быть числом)
        if not sku.isdigit():
            print("Ошибка: SKU должен быть числом.") # Можно добавить flash сообщение для пользователя
            return redirect(url_for('index'))

        data_manager.add_item_to_track(sku, query)
    else:
        print("Ошибка: SKU и поисковый запрос не могут быть пустыми.") # Можно добавить flash сообщение

    return redirect(url_for('index'))

@app.route('/remove', methods=['POST'])
def remove_item():
    """Удаляет товар из списка отслеживания."""
    sku = request.form.get('sku')
    query = request.form.get('query')
    if sku and query:
        data_manager.remove_item_from_track(sku, query)
    return redirect(url_for('index'))

@app.route('/check')
def check_positions_start():
    """Запускает проверку позиций в фоновом потоке."""
    with check_status_lock:
        if check_status["running"]:
            print("Проверка уже запущена.")
            # Можно добавить flash-сообщение пользователю
            return redirect(url_for('index'))

    # Запускаем проверку в отдельном потоке
    thread = threading.Thread(target=background_check_positions, daemon=True)
    thread.start()
    update_status(running=True, message="Запуск проверки...") # Устанавливаем статус сразу
    print("Фоновая проверка инициирована.")

    return redirect(url_for('index'))

@app.route('/check_status')
def get_check_status():
    """Возвращает текущий статус фоновой проверки."""
    with check_status_lock:
        # Возвращаем копию словаря, чтобы избежать проблем с многопоточностью при чтении
        status_copy = check_status.copy()
    return jsonify(status_copy)

if __name__ == '__main__':
    # Убедимся, что папка templates существует (Flask этого требует)
    import os
    if not os.path.exists('templates'):
        os.makedirs('templates')
    # Создадим пустой index.html, если его нет, чтобы Flask не ругался при старте
    # (хотя мы его создали ранее)
    if not os.path.exists('templates/index.html'):
        with open('templates/index.html', 'w') as f:
            f.write('<html><body>Пустой шаблон</body></html>')

    app.run(debug=True) 