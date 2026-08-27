"""URL-маршруты приложения orders."""
from django.urls import path

from .views import (
    CartItemView,
    CartView,
    ContactListCreateView,
    OrderConfirmView,
    OrderDetailView,
    OrderListView,
)

urlpatterns = [
    # Корзина
    path('basket/', CartView.as_view(), name='cart'),
    path('basket/<int:pk>/', CartItemView.as_view(), name='cart-item'),
    # Контакты (адреса доставки)
    path('contacts/', ContactListCreateView.as_view(), name='contacts'),
    # Заказы
    path('order-confirm/', OrderConfirmView.as_view(), name='order-confirm'),
    path('orders/', OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
]