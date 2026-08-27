"""
Генерирует postman_collection.json — готовую коллекцию Postman
со всеми запросами API дипломного проекта.

Запуск:  python scripts/generate_postman_collection.py
Затем в Postman: Import -> выбрать файл postman_collection.json.
"""
import json
from pathlib import Path

BASE = '{{base_url}}'
CONTENT_TYPE = {'key': 'Content-Type', 'value': 'application/json'}
AUTH = {'key': 'Authorization', 'value': 'Token {{token}}'}

# После успешного входа сохраняем токен в переменную коллекции
SAVE_TOKEN = [
    'if (pm.response.code === 200) {',
    "    pm.collectionVariables.set('token', pm.response.json().token);",
    '}',
]


def make_url(path):
    """
    Собирает URL в формате Postman v2.1 (raw + host + path + query).
    Пустая строка в конце path — это завершающий слэш '/'.
    """
    clean = path.split('?')[0]
    url = {
        'raw': BASE + path,
        'host': ['{{base_url}}'],
        'path': clean.strip('/').split('/') + [''],
    }
    if '?' in path:
        url['query'] = [
            {'key': pair.split('=')[0], 'value': pair.split('=')[1]}
            for pair in path.split('?')[1].split('&')
        ]
    return url


def request(name, method, path, body=None, auth=False):
    """Собирает один запрос Postman."""
    headers = []
    if body is not None:
        headers.append(CONTENT_TYPE)
    if auth:
        headers.append(AUTH)
    item = {
        'name': name,
        'request': {
            'method': method,
            'header': headers,
            'url': make_url(path),
        },
    }
    if body is not None:
        item['request']['body'] = {
            'mode': 'raw',
            'raw': json.dumps(body, ensure_ascii=False, indent=2),
        }
    if 'login' in name:
        item['event'] = [{
            'listen': 'test',
            'script': {'exec': SAVE_TOKEN, 'type': 'text/javascript'},
        }]
    return item


collection = {
    'info': {
        'name': 'diplom-shop-api',
        'description': 'Дипломный проект: API сервиса заказа товаров (Django + DRF)',
        'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json',
    },
    'variable': [
        {'key': 'base_url', 'value': 'http://127.0.0.1:8000'},
        {'key': 'token', 'value': ''},
    ],
    'item': [
        {'name': 'users', 'item': [
            request('register', 'POST', '/api/auth/register/', {
                'last_name': 'Иванов', 'first_name': 'Иван',
                'email': 'ivanov@example.com', 'password': 'Test12345!',
            }),
            request('login', 'POST', '/api/auth/login/', {
                'email': 'ivanov@example.com', 'password': 'Test12345!',
            }),
            request('login admin', 'POST', '/api/auth/login/', {
                'email': 'admin@diplom.local', 'password': 'Diplom2026!',
            }),
        ]},
        {'name': 'shop', 'item': [
            request('list shops', 'GET', '/api/shop/', auth=True),
            request('искать товары', 'GET', '/api/shop/?search=iPhone', auth=True),
            request('фильтр по цене', 'GET', '/api/shop/?price_max=2000', auth=True),
            request('карточка товара', 'GET', '/api/shop/1/', auth=True),
        ]},
        {'name': 'basket', 'item': [
            request('добавить в корзину', 'POST', '/api/basket/',
                    {'product': 1, 'quantity': 1}, auth=True),
            request('содержимое корзины', 'GET', '/api/basket/', auth=True),
            request('изменить количество', 'PUT', '/api/basket/1/',
                    {'quantity': 3}, auth=True),
            request('удалить из корзины', 'DELETE', '/api/basket/1/', auth=True),
        ]},
        {'name': 'contacts', 'item': [
            request('создать контакт', 'POST', '/api/contacts/', {
                'last_name': 'Иванов', 'first_name': 'Иван',
                'middle_name': 'Иванович', 'email': 'ivanov@example.com',
                'phone': '+79001234567', 'city': 'Москва',
                'street': 'Ленина', 'house': '10', 'apartment': '5',
            }, auth=True),
            request('мои контакты', 'GET', '/api/contacts/', auth=True),
            request('удалить контакт', 'DELETE', '/api/contacts/2/', auth=True),
        ]},
        {'name': 'orders', 'item': [
            request('подтвердить заказ', 'POST', '/api/order-confirm/',
                    {'basket': 1, 'contact': 1}, auth=True),
            request('мои заказы', 'GET', '/api/orders/', auth=True),
            request('детали заказа', 'GET', '/api/orders/1/', auth=True),
            request('сменить статус (админ)', 'PATCH', '/api/orders/1/status/',
                    {'status': 'processing'}, auth=True),
        ]},
    ],
}

out = Path(__file__).resolve().parents[1] / 'postman_collection.json'
out.write_text(json.dumps(collection, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Коллекция создана: {out}')