"""Регистрация моделей заказов в админке Django."""
from django.contrib import admin

from .models import Cart, CartItem, Contact, Order, OrderItem


class CartItemInline(admin.TabularInline):
    """Позиции корзины — прямо на странице корзины."""

    model = CartItem
    extra = 0


class OrderItemInline(admin.TabularInline):
    """Позиции заказа — прямо на странице заказа."""

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
    list_display = ('number', 'user', 'status', 'total_amount', 'created_at')
    list_filter = ('status',)
    search_fields = ('number', 'user__username')
    inlines = (OrderItemInline,)