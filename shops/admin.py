"""
Админка каталога + кнопка запуска импорта через Celery.
"""
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html

from shops.tasks import do_import

from .models import Category, Product, ProductParameter, Shop


class ProductParameterInline(admin.TabularInline):
    model = ProductParameter
    extra = 1


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'owner', 'accepts_orders', 'created_at')
    list_filter = ('accepts_orders',)
    search_fields = ('name',)

    # Добавляем кнопку "Запустить импорт" в список действий и на страницу магазина
    change_list_template = 'admin/shops/shop/change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'run-import/',
                self.admin_site.admin_view(self.run_import_view),
                name='shops_shop_run_import',
            ),
        ]
        return custom_urls + urls

    def run_import_view(self, request):
        """
        Запускает Celery-задачу do_import (все YAML-файлы из папки data/).
        Возвращает пользователя обратно на список магазинов.
        """
        result = do_import.delay()
        messages.success(
            request,
            f'Импорт запущен в фоне (Celery task {result.id}). '
            f'Смотрите логи воркера для результата.',
        )
        return redirect(reverse('admin:shops_shop_changelist'))


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'shop', 'external_id')
    list_filter = ('shop',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'shop', 'category', 'price', 'quantity')
    list_filter = ('shop', 'category')
    search_fields = ('name', 'model')
    inlines = (ProductParameterInline,)