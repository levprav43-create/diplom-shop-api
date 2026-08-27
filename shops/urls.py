"""URL-маршруты приложения shops."""
from django.urls import path

from .views import (
    CategoryListView,
    ProductDetailView,
    ProductListView,
    ShopListView,
)

urlpatterns = [
    path('shops/', ShopListView.as_view(), name='shop-list'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('shop/', ProductListView.as_view(), name='product-list'),
    path('shop/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
]