import json
import os
from datetime import datetime

DATA_DIR = 'data'
ITEMS_FILE = os.path.join(DATA_DIR, 'items_to_track.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'tracking_history.json')

# Убедимся, что директория для данных существует
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def _load_json(filepath, default_value):
    """Вспомогательная функция для загрузки JSON файла."""
    if not os.path.exists(filepath):
        return default_value
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print(f"Ошибка чтения файла {filepath} или файл поврежден. Возвращаем значение по умолчанию.")
        return default_value

def _save_json(filepath, data):
    """Вспомогательная функция для сохранения данных в JSON файл."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"Ошибка записи в файл {filepath}: {e}")

def load_items_to_track():
    """Загружает список товаров для отслеживания."""
    return _load_json(ITEMS_FILE, [])

def save_items_to_track(items):
    """Сохраняет список товаров для отслеживания."""
    _save_json(ITEMS_FILE, items)

def add_item_to_track(sku, query):
    """Добавляет новый товар в список отслеживания, избегая дубликатов."""
    items = load_items_to_track()
    # Проверяем, нет ли уже такой пары SKU-запрос
    if not any(item['sku'] == sku and item['query'] == query for item in items):
        items.append({'sku': sku, 'query': query})
        save_items_to_track(items)
        print(f"Добавлен товар: SKU={sku}, Запрос='{query}'")
    else:
        print(f"Товар уже отслеживается: SKU={sku}, Запрос='{query}'")

def remove_item_from_track(sku, query):
    """Удаляет товар из списка отслеживания."""
    items = load_items_to_track()
    initial_length = len(items)
    items = [item for item in items if not (item['sku'] == sku and item['query'] == query)]
    if len(items) < initial_length:
        save_items_to_track(items)
        print(f"Удален товар: SKU={sku}, Запрос='{query}'")
    else:
        print(f"Товар не найден для удаления: SKU={sku}, Запрос='{query}'")

def load_tracking_data():
    """Загружает всю историю отслеживания позиций."""
    # Данные хранятся в формате: { "sku_query": [ { "timestamp": ..., "data": ... }, ... ] }
    return _load_json(HISTORY_FILE, {})

def save_tracking_data(history):
    """Сохраняет всю историю отслеживания позиций."""
    _save_json(HISTORY_FILE, history)

def add_position_record(sku, query, position_data):
    """Добавляет новую запись о позиции товара в историю."""
    history = load_tracking_data()
    item_key = f"{sku}_{query}" # Уникальный ключ для пары SKU-запрос

    if item_key not in history:
        history[item_key] = []

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    record = {
        'timestamp': timestamp,
        **position_data # Добавляем все данные из position_data (absolute_position, page, position_on_page)
    }
    history[item_key].append(record)
    save_tracking_data(history)
    print(f"Записана позиция для {item_key} ({timestamp}): {position_data}") 