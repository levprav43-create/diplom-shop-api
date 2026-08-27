"""URL-маршруты приложения shops."""
from django.urls import path

from .views import ProductDetailView, ProductListView

urlpatterns = [
    path('shop/', ProductListView.as_view(), name='product-list'),
    path('shop/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
]