"""URL-маршруты приложения orders."""
from django.urls import path

from .views import CartItemView, CartView

urlpatterns = [
    path('basket/', CartView.as_view(), name='cart'),
    path('basket/<int:pk>/', CartItemView.as_view(), name='cart-item'),
]