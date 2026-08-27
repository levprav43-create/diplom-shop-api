"""
Расширенная админка заказов: массовые действия, фильтры,
автоуведомления клиентов через Celery.
"""
from django.conf import settings
from django.contrib import admin, messages
from django.utils.html import format_html

from orders.tasks import send_email

from .models import Cart, CartItem, Contact, Order, OrderItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('id', 'last_name', 'first_name', 'city', 'phone', 'user')
    search_fields = ('last_name', 'first_name', 'phone', 'email')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'total_amount')
    inlines = (CartItemInline,)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Расширенная админка заказов:
    - Массовые действия для смены статуса
    - Автоуведомление клиента через Celery при смене статуса
    - Фильтры, поиск, цветовая индикация
    """

    list_display = (
        'number', 'user', 'status_display', 'total_amount',
        'contact_short', 'created_at',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('number', 'user__username', 'user__email', 'contact__last_name')
    date_hierarchy = 'created_at'
    inlines = (OrderItemInline,)
    readonly_fields = ('number', 'created_at')

    actions = [
        'mark_as_processing',
        'mark_as_shipped',
        'mark_as_completed',
        'mark_as_cancelled',
    ]

    def status_display(self, obj):
        colors = {
            'new': '#0070f3',
            'processing': '#f5a623',
            'shipped': '#50e3c2',
            'completed': '#4caf50',
            'cancelled': '#d0021b',
        }
        color = colors.get(obj.status, '#666')
        return format_html(
            '<span style="color:{};font-weight:bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_display.short_description = 'Статус'

    def contact_short(self, obj):
        return f'{obj.contact.last_name} {obj.contact.first_name}, {obj.contact.city}'

    contact_short.short_description = 'Контакт'

    def save_model(self, request, obj, form, change):
        if change:
            old_status = Order.objects.get(pk=obj.pk).status
            super().save_model(request, obj, form, change)
            if old_status != obj.status:
                self._notify_status_change(order=obj, old_status=old_status)
                messages.success(
                    request,
                    f'Заказ №{obj.number}: статус изменён, клиент уведомлён (через Celery).',
                )
        else:
            super().save_model(request, obj, form, change)

    def _notify_status_change(self, order, old_status):
        old_display = dict(Order.Status.choices)[old_status]
        send_email.delay(
            subject=f'Статус заказа №{order.number} изменён',
            message=(
                f'Здравствуйте, {order.user.first_name}!\n\n'
                f'Статус вашего заказа №{order.number} изменён.\n\n'
                f'Было: {old_display}\n'
                f'Стало: {order.get_status_display()}\n\n'
                f'Итого: {order.total_amount} руб.\n'
                f'Адрес доставки: {order.contact.full_address}\n\n'
                f'Спасибо за покупку!'
            ),
            recipient_list=[order.user.email],
        )

    @admin.action(description='Отметить выбранные заказы как "В обработке"')
    def mark_as_processing(self, request, queryset):
        return self._bulk_update_status(request, queryset, Order.Status.PROCESSING)

    @admin.action(description='Отметить выбранные заказы как "Отправлен"')
    def mark_as_shipped(self, request, queryset):
        return self._bulk_update_status(request, queryset, Order.Status.SHIPPED)

    @admin.action(description='Отметить выбранные заказы как "Завершён"')
    def mark_as_completed(self, request, queryset):
        return self._bulk_update_status(request, queryset, Order.Status.COMPLETED)

    @admin.action(description='Отменить выбранные заказы')
    def mark_as_cancelled(self, request, queryset):
        return self._bulk_update_status(request, queryset, Order.Status.CANCELLED)

    def _bulk_update_status(self, request, queryset, new_status):
        updated_count = 0
        for order in queryset:
            old_status = order.status
            if old_status != new_status:
                order.status = new_status
                order.save()
                self._notify_status_change(order=order, old_status=old_status)
                updated_count += 1

        if updated_count > 0:
            self.message_user(
                request,
                f'Обновлено заказов: {updated_count}. Клиенты уведомлены (через Celery).',
                messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                'Ни один заказ не обновлён.',
                messages.INFO,
            )