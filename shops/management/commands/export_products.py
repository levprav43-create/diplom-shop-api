"""
Управляющая команда экспорта товаров в YAML.

Использование:
    python manage.py export_products   # -> exports/products.yaml
"""
from pathlib import Path

import yaml
from django.core.management.base import BaseCommand

from shops.exporter import build_export_data


class Command(BaseCommand):
    help = 'Экспортирует товары в YAML-файл (exports/products.yaml)'

    def handle(self, *args, **options):
        data = build_export_data()
        out_dir = Path(__file__).resolve().parents[3] / 'exports'
        out_dir.mkdir(exist_ok=True)
        out_file = out_dir / 'products.yaml'
        with open(out_file, 'w', encoding='utf-8') as file:
            yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False)
        self.stdout.write(self.style.SUCCESS(f'Экспорт завершён: {out_file}'))