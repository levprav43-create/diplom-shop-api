# diplom-shop-api — сервис заказа товаров (дипломный проект)

Backend-часть сервиса автоматизации закупок для розничных сетей.
Разработано на Django + Django REST Framework по спецификации Нетологии.

## Стек

- Python 3.13, Django 5.2, Django REST Framework 3.16
- PostgreSQL 15 и Redis 7 (в Docker)
- Celery для асинхронных задач (письма, импорт)
- PyYAML (импорт/экспорт товаров), token-аутентификация DRF

## Запуск проекта

### Вариант 1: Полностью в Docker (рекомендуется)

1. Создайте файл .env в корне проекта:

    SECRET_KEY=django-insecure-diplom-project-key-2026
    DEBUG=True
    DB_NAME=diplom_db
    DB_USER=diplom_user
    DB_PASSWORD=diplom_password
    DB_HOST=localhost
    DB_PORT=5433
    REDIS_HOST=localhost
    DEFAULT_FROM_EMAIL=shop@diplom.local
    ADMIN_EMAIL=admin@diplom.local

2. Соберите и запустите все контейнеры (web, worker, db, redis):

    docker compose up --build -d

3. Примените миграции:

    docker compose exec web python manage.py migrate

4. Импортируйте товары:

    docker compose exec web python manage.py import_products

5. Создайте суперпользователя:

    docker compose exec web python manage.py createsuperuser

6. Проверьте логи воркера:

    docker compose logs -f worker

- API: http://localhost:8000/api/
- Админка: http://localhost:8000/admin/
- Остановка: docker compose down

### Вариант 2: Локально (для разработки)

1. Создайте .env (тот же, что выше)
2. Запустите БД и Redis: docker compose up db redis -d
3. Создайте окружение и зависимости:

    python -m venv venv
    venv\Scripts\activate        (Windows)
    source venv/bin/activate     (Linux/MacOS)
    pip install -r requirements.txt

4. Миграции и данные:

    python manage.py migrate
    python manage.py import_products
    python manage.py createsuperuser

5. Запустите сервер и воркер в разных терминалах:

    python manage.py runserver
    celery -A config worker -l INFO --pool=solo

## Тестовые пользователи

- Администратор: admin@diplom.local / Diplom2026!
- Клиент: ivanov@example.com / Test12345!
- Поставщик: partner@example.com / Partner123!

## API эндпоинты

### Аутентификация
- POST /api/auth/register/ — регистрация (приветственное письмо)
- POST /api/auth/login/ — вход по email (возвращает токен)
- POST /api/auth/password-reset/ — восстановление пароля
- POST /api/auth/password-reset-confirm/ — установка нового пароля

### Каталог
- GET /api/shops/ — список магазинов
- GET /api/categories/ — список категорий (?shop=<id>)
- GET /api/shop/ — товары (search, category, shop, price_min, price_max)
- GET /api/shop/<id>/ — карточка товара с характеристиками
- GET /api/shop/export/ — экспорт товаров в YAML

### Корзина
- GET /api/basket/ — корзина
- POST /api/basket/ — добавить товар
- PUT /api/basket/<id>/ — изменить количество
- DELETE /api/basket/<id>/ — удалить позицию

### Контакты
- GET /api/contacts/ — мои адреса доставки
- POST /api/contacts/ — создать адрес
- DELETE /api/contacts/<id>/ — удалить адрес

### Заказы
- POST /api/order-confirm/ — подтверждение заказа (basket + contact)
- GET /api/orders/ — история заказов
- GET /api/orders/<id>/ — детали заказа
- PATCH /api/orders/<id>/status/ — смена статуса (админ)

### Блок партнёра
- POST /api/partner/update/ — загрузить прайс (multipart, поле file)
- GET /api/partner/status/ — статус приёма заказов
- PUT /api/partner/status/ — вкл/выкл приём заказов
- GET /api/partner/orders/ — заказы с товарами партнёра

## Управление данными

- Импорт: python manage.py import_products [файл.yaml]
- Экспорт: python manage.py export_products (-> exports/products.yaml)
- Формат экспорта совместим с импортом (round-trip)

## Админка склада

http://127.0.0.1:8000/admin/ (admin / Diplom2026!)

- Заказы: цветные статусы, фильтры, поиск, массовые действия
- Смена статуса — автоуведомление клиента (через Celery)
- Магазины: кнопка «Запустить импорт товаров (Celery)»
- Товары: настраиваемые характеристики inline

## Celery

- send_email — асинхронная отправка писем
- do_import — асинхронный импорт (кнопка в админке)
- Воркер: celery -A config worker -l INFO --pool=solo

## Postman

В репозитории лежит postman_collection.json — готовая коллекция запросов.
Импорт: Postman -> Import -> выбрать файл.
Запрос login автоматически сохраняет токен в переменную token.

## Структура проекта

- shops — каталог, импорт/экспорт, блок партнёра
- users — регистрация, вход, восстановление пароля
- orders — корзина, контакты, заказы, расширенная админка
- config — настройки Django и Celery
