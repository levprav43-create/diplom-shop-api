"""
Конфигурация Celery дипломного проекта.

Брокер и бэкенд результатов — Redis (хост читается из переменной окружения
REDIS_HOST, по умолчанию localhost для локальной разработки).
"""
import os

from celery import Celery
from decouple import config

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('diplom_shop_api')

redis_host = config('REDIS_HOST', default='localhost')
app.conf.broker_url = f'redis://{redis_host}:6379/0'
app.conf.result_backend = f'redis://{redis_host}:6379/0'

app.autodiscover_tasks()