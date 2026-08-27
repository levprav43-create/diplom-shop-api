"""API-вьюхи приложения shops: список товаров и детальная карточка."""
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Product
from .serializers import ProductDetailSerializer, ProductListSerializer


class ProductListView(APIView):
    """
    Список товаров с фильтрацией и поиском.

    Поддерживаемые query-параметры:
    - search    — поиск по названию и модели
    - category  — ID категории
    - shop      — ID магазина
    - price_min — минимальная цена
    - price_max — максимальная цена
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        queryset = Product.objects.select_related('shop', 'category').all()

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(model__icontains=search)
            )

        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)

        shop = request.query_params.get('shop')
        if shop:
            queryset = queryset.filter(shop_id=shop)

        price_min = request.query_params.get('price_min')
        if price_min:
            queryset = queryset.filter(price__gte=price_min)

        price_max = request.query_params.get('price_max')
        if price_max:
            queryset = queryset.filter(price__lte=price_max)

        serializer = ProductListSerializer(queryset, many=True)
        return Response(serializer.data)


class ProductDetailView(APIView):
    """Детальная карточка товара со всеми характеристиками."""

    permission_classes = (IsAuthenticated,)

    def get(self, request, pk):
        try:
            product = Product.objects.select_related(
                'shop', 'category'
            ).prefetch_related('parameters').get(pk=pk)
        except Product.DoesNotExist:
            return Response(
                {'detail': 'Товар не найден'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ProductDetailSerializer(product)
        return Response(serializer.data)