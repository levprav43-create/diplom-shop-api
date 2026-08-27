"""Корневая конфигурация URL дипломного проекта."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/', include('shops.urls')),
    path('api/', include('orders.urls')),
]