"""Сериализаторы приложения orders: корзина и её позиции."""
from rest_framework import serializers

from shops.models import Product
from shops.serializers import ProductListSerializer

from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    """Позиция корзины: товар + количество + сумма."""

    product = ProductListSerializer(read_only=True)
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = CartItem
        fields = ('id', 'product', 'quantity', 'amount')


class CartSerializer(serializers.ModelSerializer):
    """Корзина: позиции + итоговая сумма + общее количество."""

    items = CartItemSerializer(many=True, read_only=True)
    total_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ('id', 'items', 'total_amount', 'products_count')


class CartItemCreateSerializer(serializers.Serializer):
    """Данные для добавления товара в корзину."""

    product = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate_product(self, value):
        """Товар должен существовать и быть в наличии."""
        try:
            product = Product.objects.get(pk=value)
        except Product.DoesNotExist:
            raise serializers.ValidationError('Товар не найден')
        if product.quantity <= 0:
            raise serializers.ValidationError('Товар закончился')
        return product

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError('Количество должно быть больше 0')
        return value


class CartItemUpdateSerializer(serializers.Serializer):
    """Данные для изменения количества товара в корзине."""

    quantity = serializers.IntegerField(min_value=1)

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError('Количество должно быть больше 0')
        return value