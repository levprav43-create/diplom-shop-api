"""
Модуль импорта прайсов поставщика из распарсенного YAML.

Используется и management-командой import_products,
и API-эндпоинтом обновления прайса партнёром.
Повторный импорт не создаёт дубли — товары обновляются.
"""
from decimal import Decimal

from django.db import transaction

from .models import Category, Product, ProductParameter, Shop


def import_shop_data(data: dict) -> dict:
    """
    Загружает данные одного магазина в БД внутри одной транзакции.

    :param data: словарь, полученный из yaml.safe_load(...)
    :return: {'shop': объект Shop, 'stats': словарь со статистикой}
    """
    stats = {'categories': 0, 'products': 0, 'parameters': 0}

    with transaction.atomic():
        # Магазин (поставщик)
        shop, _ = Shop.objects.get_or_create(name=data['shop'])

        # Категории: запоминаем соответствие «внешний id -> категория»
        categories = {}
        for item in data.get('categories', []):
            category, _ = Category.objects.update_or_create(
                shop=shop,
                external_id=item['id'],
                defaults={'name': item['name']},
            )
            categories[item['id']] = category
            stats['categories'] += 1

        # Товары
        for item in data.get('goods', []):
            product, _ = Product.objects.update_or_create(
                shop=shop,
                external_id=item['id'],
                defaults={
                    'category': categories[item['category']],
                    'model': item['model'],
                    'name': item['name'],
                    'price': Decimal(str(item['price'])),
                    'price_rrc': Decimal(str(item['price_rrc'])),
                    'quantity': item['quantity'],
                },
            )
            stats['products'] += 1

            # Настраиваемые характеристики товара
            for name, value in item.get('parameters', {}).items():
                ProductParameter.objects.update_or_create(
                    product=product,
                    name=name,
                    defaults={'value': str(value)},
                )
                stats['parameters'] += 1

    return {'shop': shop, 'stats': stats}