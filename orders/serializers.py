"""Сериализаторы приложения orders: корзина, контакты, заказы."""
from rest_framework import serializers

from shops.models import Product
from shops.serializers import ProductListSerializer

from .models import Cart, CartItem, Contact, Order, OrderItem


# ==================== КОРЗИНА ====================


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


# ==================== КОНТАКТЫ ====================


class ContactSerializer(serializers.ModelSerializer):
    """Контакт (адрес доставки) — создание и просмотр."""

    full_address = serializers.CharField(read_only=True)

    class Meta:
        model = Contact
        fields = (
            'id', 'last_name', 'first_name', 'middle_name',
            'email', 'phone', 'address',
            'city', 'street', 'house', 'building', 'structure', 'apartment',
            'full_address', 'created_at',
        )
        read_only_fields = ('created_at',)


# ==================== ЗАКАЗЫ ====================


class OrderItemSerializer(serializers.ModelSerializer):
    """Позиция заказа со снапшотом цены на момент покупки."""

    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = OrderItem
        fields = ('id', 'product_name', 'price', 'quantity', 'amount')


class OrderSerializer(serializers.ModelSerializer):
    """Заказ: номер, дата, статус, сумма + позиция доставки."""

    items = OrderItemSerializer(many=True, read_only=True)
    contact = ContactSerializer(read_only=True)
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )

    class Meta:
        model = Order
        fields = (
            'id', 'number', 'status', 'status_display',
            'total_amount', 'created_at',
            'contact', 'items',
        )


class OrderListSerializer(serializers.ModelSerializer):
    """Краткое представление заказа для списка (история)."""

    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )

    class Meta:
        model = Order
        fields = (
            'id', 'number', 'status', 'status_display',
            'total_amount', 'created_at',
        )


class OrderConfirmSerializer(serializers.Serializer):
    """
    Подтверждение заказа по спецификации ТЗ:
    принимает ID корзины и ID контакта.
    """

    basket = serializers.IntegerField()
    contact = serializers.IntegerField()

    def validate(self, attrs):
        user = self.context['request'].user

        # Корзина должна принадлежать пользователю и быть непустой
        try:
            basket = Cart.objects.get(pk=attrs['basket'], user=user)
        except Cart.DoesNotExist:
            raise serializers.ValidationError(
                {'basket': 'Корзина не найдена или не принадлежит вам'}
            )
        if not basket.items.exists():
            raise serializers.ValidationError(
                {'basket': 'Корзина пуста — нечего заказывать'}
            )

        # Контакт должен принадлежать пользователю
        try:
            contact = Contact.objects.get(pk=attrs['contact'], user=user)
        except Contact.DoesNotExist:
            raise serializers.ValidationError(
                {'contact': 'Контакт не найден или не принадлежит вам'}
            )

        attrs['basket_obj'] = basket
        attrs['contact_obj'] = contact
        return attrs