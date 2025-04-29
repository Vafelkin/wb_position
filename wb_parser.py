import requests
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import quote_plus

# Базовые заголовки для имитации браузера
HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive',
    'Origin': 'https://www.wildberries.ru',
    'Referer': 'https://www.wildberries.ru/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36',
    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="100", "Google Chrome";v="100"' # Пример заголовка
}

# Максимальное количество страниц для проверки
MAX_PAGES_TO_CHECK = 10
# Количество товаров на одной странице (стандартное для WB, может меняться)
PRODUCTS_PER_PAGE = 100

def get_product_position(sku, query, status_updater=None):
    """Получает позицию товара по SKU в поисковой выдаче WB по заданному запросу.

    Args:
        sku (str): Артикул товара.
        query (str): Поисковый запрос.
        status_updater (callable, optional): Функция для обновления статуса,
                                             принимает номер текущей страницы.
                                             Defaults to None.
    """
    print(f"[Parser] Ищем SKU {sku} по запросу '{query}'")
    target_sku = int(sku) # Убедимся, что SKU - это число

    encoded_query = quote_plus(query) # Кодируем запрос для URL

    for page_num in range(1, MAX_PAGES_TO_CHECK + 1):
        # Обновляем статус перед запросом страницы
        if status_updater:
            try:
                status_updater(page_num)
            except Exception as e:
                print(f"[Parser] Ошибка при вызове status_updater: {e}")

        print(f"[Parser] Проверяем страницу {page_num}")
        search_url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?appType=1&couponsGeo=12,3,18,15,21&curr=rub&dest=-1257786&emp=0&lang=ru&locale=ru&page={page_num}&pricemarginCoeff=1.0&query={encoded_query}&reg=0&regions=80,64,38,4,115,83,33,68,70,69,30,86,75,40,1,66,48,110,31,22,71,114&resultset=catalog&sort=popular&spp=0&suppressSpellcheck=false"

        try:
            response = requests.get(search_url, headers=HEADERS, timeout=15)
            response.raise_for_status() # Проверка на ошибки HTTP (4xx, 5xx)
            data = response.json()

            if not data or 'data' not in data or 'products' not in data['data']:
                print(f"[Parser] Не удалось получить данные о товарах со страницы {page_num}.")
                # Можно добавить обработку, если структура ответа изменилась
                time.sleep(random.uniform(1, 3)) # Пауза перед следующей страницей
                continue

            products_on_page = data['data']['products']
            if not products_on_page:
                print(f"[Parser] Товары не найдены на странице {page_num}. Завершаем поиск.")
                return None # Товар не найден

            # Ищем SKU среди товаров на странице
            for index, product in enumerate(products_on_page):
                if product.get('id') == target_sku:
                    position_on_page = index + 1
                    absolute_position = (page_num - 1) * PRODUCTS_PER_PAGE + position_on_page
                    result = {
                        'absolute_position': absolute_position,
                        'page': page_num,
                        'position_on_page': position_on_page
                    }
                    print(f"[Parser] SKU {sku} найден! Позиция: {result}")
                    return result

            # Небольшая пауза между запросами страниц, чтобы не перегружать сервер
            time.sleep(random.uniform(1, 3))

        except requests.exceptions.RequestException as e:
            print(f"[Parser] Ошибка при запросе страницы {page_num}: {e}")
            # Можно добавить повторные попытки или другую логику обработки ошибок
            time.sleep(random.uniform(2, 5)) # Увеличенная пауза при ошибке
            continue # Пропускаем эту страницу при ошибке
        except json.JSONDecodeError:
             print(f"[Parser] Ошибка декодирования JSON со страницы {page_num}. Возможно, изменился формат ответа.")
             time.sleep(random.uniform(2, 5))
             continue

    print(f"[Parser] SKU {sku} не найден в первых {MAX_PAGES_TO_CHECK} страницах.")
    return None # Товар не найден в пределах MAX_PAGES_TO_CHECK

# Пример использования (для тестирования модуля)
if __name__ == '__main__':
    test_sku = "142380908" # Пример SKU (замените на реальный для теста)
    test_query = "робот пылесос" # Пример запроса

    # Тестируем с пробелом
    test_query_with_space = "чехол на айфон"
    print(f"Тестируем кодирование: '{test_query_with_space}' -> '{quote_plus(test_query_with_space)}'")

    # Пример вызова с status_updater (просто печатает страницу)
    def simple_status_update(page):
        print(f"---> Тест status_updater: Проверяется страница {page}")

    position = get_product_position(test_sku, test_query_with_space, status_updater=simple_status_update)

    if position:
        print(f"\nИтоговая позиция для SKU {test_sku} по запросу '{test_query_with_space}':")
        print(f"  Абсолютная позиция: {position['absolute_position']}")
        print(f"  Страница: {position['page']}")
        print(f"  Позиция на странице: {position['position_on_page']}")
    else:
        print(f"\nТовар с SKU {test_sku} не найден по запросу '{test_query_with_space}'.") 