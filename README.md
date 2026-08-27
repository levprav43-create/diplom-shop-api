# diplom-shop-api — сервис заказа товаров (дипломный проект)

Backend-часть сервиса автоматизации закупок для розничных сетей.
Разработано на Django + Django REST Framework по спецификации Нетологии.

## Стек

- Python 3.13, Django 5.2, Django REST Framework 3.16
- PostgreSQL 15 и Redis 7 (в Docker)
- PyYAML (импорт товаров), token-аутентификация DRF

## Запуск проекта

### 1. Требования
- Docker Desktop (запущен)
- Python 3.13

### 2. Файл .env
Создайте файл .env в корне проекта:

    SECRET_KEY=your-secret-key
    DEBUG=True

### 3. Запустить БД и Redis
    docker compose up -d

### 4. Установить зависимости
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt

### 5. Миграции и данные
    python manage.py migrate
    python manage.py import_products
    python manage.py createsuperuser

### 6. Запуск сервера
    python manage.py runserver

- API: http://127.0.0.1:8000/api/
- Админка: http://127.0.0.1:8000/admin/

## API эндпоинты

- POST /api/auth/register/ — регистрация
- POST /api/auth/login/ — вход (возвращает токен)
- GET /api/shop/ — список товаров (поиск и фильтры: search, category, shop, price_min, price_max)
- GET /api/shop/<id>/ — карточка товара с характеристиками
- GET /api/basket/ — корзина
- POST /api/basket/ — добавить товар
- PUT /api/basket/<id>/ — изменить количество
- DELETE /api/basket/<id>/ — удалить позицию
- GET /api/contacts/ — мои адреса доставки
- POST /api/contacts/ — создать адрес доставки
- DELETE /api/contacts/<id>/ — удалить адрес
- POST /api/order-confirm/ — подтверждение заказа (basket + contact)
- GET /api/orders/ — история заказов
- GET /api/orders/<id>/ — детали заказа
- PATCH /api/orders/<id>/status/ — смена статуса заказа (админ)

## Postman

В репозитории лежит postman_collection.json — готовая коллекция запросов.
Импорт: Postman -> Import -> выбрать файл.
Запрос login автоматически сохраняет токен в переменную token.

## Структура проекта

- shops — каталог: магазины, категории, товары, характеристики, импорт
- users — регистрация и вход
- orders — корзина, контакты, заказы
