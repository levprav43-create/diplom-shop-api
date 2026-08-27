"""
Конфигурация Celery дипломного проекта.

Брокер и бэкенд результатов — Redis, поднятый в Docker (порт 6379).
Задачи автоматически обнаруживаются в tasks.py всех приложений.
"""
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('diplom_shop_api')

# Брокер (очередь задач) и хранилище результатов — Redis
app.conf.broker_url = 'redis://127.0.0.1:6379/0'
app.conf.result_backend = 'redis://127.0.0.1:6379/0'

# Ищем задачи в tasks.py всех установленных приложений
app.autodiscover_tasks()