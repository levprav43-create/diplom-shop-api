"""
Управляющая команда импорта товаров из YAML-файлов.

Использование:
    python manage.py import_products                  # все файлы из папки data/
    python manage.py import_products data/shop1.yaml  # один конкретный файл

Повторный запуск не создаёт дубликаты: существующие товары
обновляются (сценарий «поставщик прислал обновлённый прайс»).
"""
from decimal import Decimal
from pathlib import Path

import yaml
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from shops.models import Category, Product, ProductParameter, Shop


class Command(BaseCommand):
    help = 'Импортирует магазины, категории и товары из YAML-файлов'

    def add_arguments(self, parser):
        parser.add_argument(
            'paths',
            nargs='*',
            type=str,
            help='Пути к YAML-файлам (по умолчанию — все файлы в папке data/)',
        )

    def handle(self, *args, **options):
        # Если пути не переданы — берём все YAML-файлы из папки data/
        paths = [Path(p) for p in options['paths']]
        if not paths:
            data_dir = Path(__file__).resolve().parents[3] / 'data'
            paths = sorted(data_dir.glob('*.yaml')) + sorted(data_dir.glob('*.yml'))
            if not paths:
                raise CommandError(f'В папке {data_dir} не найдено ни одного YAML-файла')

        for path in paths:
            if not path.is_file():
                raise CommandError(f'Файл не найден: {path}')
            self.import_file(path)

        self.stdout.write(self.style.SUCCESS('Импорт завершён!'))

    def import_file(self, path: Path) -> None:
        """Импортирует один YAML-файл внутри одной транзакции."""
        with open(path, encoding='utf-8') as file:
            data = yaml.safe_load(file)

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

        self.stdout.write(
            self.style.SUCCESS(
                f'{path.name}: магазин «{shop.name}» — '
                f'категорий: {stats["categories"]}, '
                f'товаров: {stats["products"]}, '
                f'характеристик: {stats["parameters"]}'
            )
        )