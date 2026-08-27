"""URL-маршруты приложения shops: каталог, экспорт и блок партнёра."""
from django.urls import path

from .views import (
    CategoryListView,
    PartnerOrdersView,
    PartnerStatusView,
    PartnerUpdateView,
    ProductDetailView,
    ProductExportView,
    ProductListView,
    ShopListView,
)

urlpatterns = [
    # Каталог (для клиентов)
    path('shops/', ShopListView.as_view(), name='shop-list'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('shop/', ProductListView.as_view(), name='product-list'),
    path('shop/export/', ProductExportView.as_view(), name='product-export'),
    path('shop/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    # Блок партнёра (поставщика)
    path('partner/update/', PartnerUpdateView.as_view(), name='partner-update'),
    path('partner/status/', PartnerStatusView.as_view(), name='partner-status'),
    path('partner/orders/', PartnerOrdersView.as_view(), name='partner-orders'),
]