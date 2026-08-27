"""API-вьюхи приложения shops: магазины, категории, товары, экспорт, партнёр."""
import yaml
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order, OrderItem
from orders.serializers import OrderListSerializer

from .exporter import build_export_data
from .importer import import_shop_data
from .models import Category, Product, Shop
from .serializers import (
    CategoryListSerializer,
    PartnerStatusSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ShopListSerializer,
)


class ShopListView(APIView):
    """Список магазинов (спецификация: list shops)."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        shops = Shop.objects.all()
        serializer = ShopListSerializer(shops, many=True)
        return Response(serializer.data)


class CategoryListView(APIView):
    """Список категорий; фильтр по магазину: ?shop=<id> (спецификация: list categories)."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        queryset = Category.objects.select_related('shop').all()
        shop = request.query_params.get('shop')
        if shop:
            queryset = queryset.filter(shop_id=shop)
        serializer = CategoryListSerializer(queryset, many=True)
        return Response(serializer.data)


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


class ProductExportView(APIView):
    """
    Экспорт товаров в YAML (скачивание файла).

    Формат совместим с импортом: файл можно снова загрузить
    через import_products или /api/partner/update/.
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        data = build_export_data()
        yaml_text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
        response = HttpResponse(
            yaml_text, content_type='text/yaml; charset=utf-8'
        )
        response['Content-Disposition'] = (
            'attachment; filename="products_export.yaml"'
        )
        return response


# ==================== БЛОК ПАРТНЁРА (ПОСТАВЩИКА) ====================


def _get_partner_shop(user):
    """
    Возвращает магазин, владельцем которого является пользователь.
    Если магазина нет — None (эндпоинт вернёт 400).
    """
    return Shop.objects.filter(owner=user).first()


class PartnerUpdateView(APIView):
    """
    Поставщик загружает YAML с обновлённым прайсом (multipart/form-data).

    POST /api/partner/update/
    Поле формы: file — YAML-файл.

    Импорт выполняется синхронно, т.к. партнёру нужен немедленный ответ
    со статистикой. Асинхронный вариант (Celery) — кнопка в админке.
    """

    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response(
                {'detail': 'Поле "file" с YAML-файлом обязательно'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = yaml.safe_load(file.read().decode('utf-8'))
        except yaml.YAMLError as exc:
            return Response(
                {'detail': f'Ошибка парсинга YAML: {exc}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        shop_name = data.get('shop')
        if not shop_name:
            return Response(
                {'detail': 'В YAML отсутствует поле "shop"'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing = Shop.objects.filter(name=shop_name).first()
        if existing and existing.owner and existing.owner != request.user:
            return Response(
                {'detail': 'Этот магазин принадлежит другому пользователю'},
                status=status.HTTP_403_FORBIDDEN,
            )

        result = import_shop_data(data)
        shop = result['shop']

        if not shop.owner:
            shop.owner = request.user
            shop.save(update_fields=['owner'])

        stats = result['stats']
        return Response({
            'shop': shop.name,
            'categories': stats['categories'],
            'products': stats['products'],
            'parameters': stats['parameters'],
        }, status=status.HTTP_200_OK)


class PartnerStatusView(APIView):
    """
    Статус приёма заказов партнёром.

    GET — текущий статус.
    PUT — переключить accepts_orders (true/false).
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        shop = _get_partner_shop(request.user)
        if not shop:
            return Response(
                {'detail': 'У вас нет магазина. Загрузите прайс через /api/partner/update/'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(PartnerStatusSerializer(shop).data)

    def put(self, request):
        shop = _get_partner_shop(request.user)
        if not shop:
            return Response(
                {'detail': 'У вас нет магазина'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        accepts_orders = request.data.get('accepts_orders')
        if accepts_orders not in (True, False):
            return Response(
                {'detail': 'Поле "accepts_orders" должно быть true или false'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        shop.accepts_orders = accepts_orders
        shop.save(update_fields=['accepts_orders'])
        return Response(PartnerStatusSerializer(shop).data)


class PartnerOrdersView(APIView):
    """
    Список заказов, содержащих товары партнёра.

    GET /api/partner/orders/ — возвращает заказы, в которых есть хотя бы
    одна позиция с товаром из его магазинов.
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        shop = _get_partner_shop(request.user)
        if not shop:
            return Response(
                {'detail': 'У вас нет магазина'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_ids = OrderItem.objects.filter(
            product__shop=shop
        ).values_list('order_id', flat=True).distinct()

        orders = Order.objects.filter(id__in=order_ids).order_by('-created_at')
        serializer = OrderListSerializer(orders, many=True)
        return Response(serializer.data)