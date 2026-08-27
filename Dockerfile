# Dockerfile для Django-приложения дипломного проекта
# Используем stable-ветку Debian (bookworm) для стабильности сборки
FROM python:3.13-bookworm

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения
COPY . .

# Создаём директории для данных и экспорта
RUN mkdir -p /app/data /app/exports

# Открываем порт для Django
EXPOSE 8000

# Команда по умолчанию: запуск Django-сервера
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]