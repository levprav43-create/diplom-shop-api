"""Сериализаторы приложения shops: магазины, категории, товары."""
from rest_framework import serializers

from .models import Category, Product, ProductParameter, Shop


class ShopSerializer(serializers.ModelSerializer):
    """Краткое представление магазина."""

    class Meta:
        model = Shop
        fields = ('id', 'name')


class ShopListSerializer(serializers.ModelSerializer):
    """Список магазинов с признаком приёма заказов."""

    class Meta:
        model = Shop
        fields = ('id', 'name', 'accepts_orders')


class CategorySerializer(serializers.ModelSerializer):
    """Краткое представление категории."""

    class Meta:
        model = Category
        fields = ('id', 'name')


class CategoryListSerializer(serializers.ModelSerializer):
    """Список категорий с привязкой к магазину."""

    shop = ShopSerializer(read_only=True)

    class Meta:
        model = Category
        fields = ('id', 'name', 'shop', 'external_id')


class ProductParameterSerializer(serializers.ModelSerializer):
    """Настраиваемая характеристика товара (имя — значение)."""

    class Meta:
        model = ProductParameter
        fields = ('name', 'value')


class ProductListSerializer(serializers.ModelSerializer):
    """Краткая карточка товара для списка."""

    shop = ShopSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'model', 'shop', 'category',
            'price', 'price_rrc', 'quantity',
        )


class ProductDetailSerializer(serializers.ModelSerializer):
    """Полная карточка товара со всеми характеристиками."""

    shop = ShopSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    parameters = ProductParameterSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'model', 'description', 'shop', 'category',
            'price', 'price_rrc', 'quantity', 'parameters',
        )