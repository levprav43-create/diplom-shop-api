"""Регистрация моделей каталога в админке Django."""
from django.contrib import admin

from .models import Category, Product, ProductParameter, Shop


class ProductParameterInline(admin.TabularInline):
    """Характеристики редактируются прямо на странице товара."""

    model = ProductParameter
    extra = 1


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'owner', 'accepts_orders', 'created_at')
    list_filter = ('accepts_orders',)
    search_fields = ('name',)


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