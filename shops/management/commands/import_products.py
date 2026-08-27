"""
Управляющая команда импорта товаров из YAML-файлов.

Использование:
    python manage.py import_products                  # все файлы из папки data/
    python manage.py import_products data/shop1.yaml  # один конкретный файл
    python manage.py import_products exports/products.yaml  # round-trip из экспорта

Поддерживаются оба формата: одиночный прайс и список прайсов (экспорт).
Вся логика загрузки живёт в shops/importer.py (принцип DRY).
"""
from pathlib import Path

import yaml
from django.core.management.base import BaseCommand, CommandError

from shops.importer import import_data


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
            with open(path, encoding='utf-8') as file:
                data = yaml.safe_load(file)

            # Поддержка обоих форматов (прайс и экспорт)
            for result in import_data(data):
                stats = result['stats']
                self.stdout.write(
                    self.style.SUCCESS(
                        f'{path.name}: магазин «{result["shop"].name}» — '
                        f'категорий: {stats["categories"]}, '
                        f'товаров: {stats["products"]}, '
                        f'характеристик: {stats["parameters"]}'
                    )
                )

        self.stdout.write(self.style.SUCCESS('Импорт завершён!'))