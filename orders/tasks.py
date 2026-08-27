"""Celery-задачи приложения orders."""
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task
def send_email(subject: str, message: str, recipient_list: list) -> dict:
    """
    Асинхронная отправка письма (задача send_email из ТЗ).

    Выполняется воркером Celery, не блокируя HTTP-запрос.
    """
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        fail_silently=False,
    )
    return {'sent_to': recipient_list, 'subject': subject}