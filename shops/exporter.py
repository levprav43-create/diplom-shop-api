"""
Модуль экспорта товаров в YAML.

Формат экспорта полностью совпадает с форматом импорта:
выгруженный файл можно снова загрузить командой import_products
(round-trip совместимость).
"""
from .models import Product, Shop


def build_export_data() -> list:
    """
    Собирает данные всех магазинов в формате прайса поставщика.

    :return: список словарей [{'shop': ..., 'categories': [...], 'goods': [...]}, ...]
    """
    result = []
    for shop in Shop.objects.prefetch_related('categories').all():
        categories = [
            {'id': category.external_id, 'name': category.name}
            for category in shop.categories.all()
        ]

        goods = []
        products = (
            Product.objects.filter(shop=shop)
            .select_related('category')
            .prefetch_related('parameters')
        )
        for product in products:
            goods.append({
                'id': product.external_id,
                'category': product.category.external_id,
                'model': product.model,
                'name': product.name,
                'price': float(product.price),
                'price_rrc': float(product.price_rrc),
                'quantity': product.quantity,
                'parameters': {
                    param.name: param.value for param in product.parameters.all()
                },
            })

        result.append({
            'shop': shop.name,
            'categories': categories,
            'goods': goods,
        })
    return result