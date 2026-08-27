"""Celery-задачи приложения shops."""
from pathlib import Path

import yaml
from celery import shared_task
from django.conf import settings

from .importer import import_shop_data


@shared_task
def do_import(path: str = None) -> dict:
    """
    Асинхронный импорт товаров (задача do_import из ТЗ).

    Без аргумента импортирует все YAML-файлы из папки data/,
    с аргументом — один конкретный файл.
    """
    # Используем BASE_DIR из settings — это всегда корень проекта
    base = Path(settings.BASE_DIR) / 'data'

    if path:
        paths = [Path(path)]
    else:
        paths = sorted(base.glob('*.yaml')) + sorted(base.glob('*.yml'))

    total = {'shops': 0, 'categories': 0, 'products': 0, 'parameters': 0}
    for file_path in paths:
        with open(file_path, encoding='utf-8') as file:
            data = yaml.safe_load(file)
        result = import_shop_data(data)
        total['shops'] += 1
        for key in ('categories', 'products', 'parameters'):
            total[key] += result['stats'][key]

    return total