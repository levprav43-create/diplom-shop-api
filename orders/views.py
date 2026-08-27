"""API-вьюхи приложения orders: корзина, контакты, заказы."""
from django.core.mail import send_mail
from django.db import transaction
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Cart, CartItem, Contact, Order, OrderItem
from .serializers import (
    CartItemCreateSerializer,
    CartItemSerializer,
    CartItemUpdateSerializer,
    CartSerializer,
    ContactSerializer,
    OrderConfirmSerializer,
    OrderListSerializer,
    OrderSerializer,
)


# ==================== КОРЗИНА ====================


class CartView(APIView):
    """
    Корзина текущего пользователя.

    GET  — получить содержимое корзины.
    POST — добавить товар (если уже есть — увеличить количество).
    """

    permission_classes = (IsAuthenticated,)

    def get_cart(self, user):
        cart, _ = Cart.objects.get_or_create(user=user)
        return cart

    def get(self, request):
        cart = self.get_cart(request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    def post(self, request):
        serializer = CartItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = self.get_cart(request.user)
        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity},
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return Response(
            CartItemSerializer(cart_item).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CartItemView(APIView):
    """
    Конкретная позиция корзины.

    PUT    — изменить количество.
    DELETE — удалить позицию.
    """

    permission_classes = (IsAuthenticated,)

    def get_item(self, request, pk):
        try:
            return CartItem.objects.select_related('product', 'product__shop').get(
                pk=pk, cart__user=request.user
            )
        except CartItem.DoesNotExist:
            return None

    def put(self, request, pk):
        item = self.get_item(request, pk)
        if item is None:
            return Response(
                {'detail': 'Позиция не найдена'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CartItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item.quantity = serializer.validated_data['quantity']
        item.save()
        return Response(CartItemSerializer(item).data)

    def delete(self, request, pk):
        item = self.get_item(request, pk)
        if item is None:
            return Response(
                {'detail': 'Позиция не найдена'},
                status=status.HTTP_404_NOT_FOUND,
            )
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==================== КОНТАКТЫ ====================


class ContactListCreateView(APIView):
    """
    Контакты (адреса доставки) текущего пользователя.

    GET  — список контактов пользователя.
    POST — создать новый контакт.
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        contacts = Contact.objects.filter(user=request.user)
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ==================== ЗАКАЗЫ ====================


class OrderConfirmView(APIView):
    """
    Подтверждение заказа (ключевой сценарий ТЗ).

    Принимает basket_id + contact_id:
    1. Создаёт заказ (Order) со снапшотом цен и названий товаров
    2. Списывает товары со склада
    3. Очищает корзину
    4. Отправляет email-подтверждение клиенту
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = OrderConfirmSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        basket = serializer.validated_data['basket_obj']
        contact = serializer.validated_data['contact_obj']

        # Всё в одной транзакции: если что-то пойдёт не так — откат
        with transaction.atomic():
            # 1. Создаём заказ
            total = basket.total_amount
            order = Order.objects.create(
                user=request.user,
                contact=contact,
                total_amount=total,
            )

            # 2. Переносим позиции корзины в позиции заказа со снапшотом
            for cart_item in basket.items.select_related('product'):
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    product_name=cart_item.product.name,
                    price=cart_item.product.price,
                    quantity=cart_item.quantity,
                )
                # Списываем товар со склада поставщика
                product = cart_item.product
                product.quantity = max(0, product.quantity - cart_item.quantity)
                product.save(update_fields=['quantity'])

            # 3. Очищаем корзину
            basket.items.all().delete()

        # 4. Отправляем email (пока в консоль, позже — Celery)
        self._send_confirmation_email(order)

        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _send_confirmation_email(order: Order) -> None:
        """Отправляет письмо-подтверждение заказа клиенту."""
        items_lines = []
        for item in order.items.all():
            items_lines.append(
                f'  • {item.product_name} × {item.quantity} '
                f'= {item.amount} руб.'
            )
        items_text = '\n'.join(items_lines) if items_lines else '(пусто)'

        send_mail(
            subject=f'Заказ №{order.number} подтверждён',
            message=(
                f'Здравствуйте, {order.user.first_name}!\n\n'
                f'Ваш заказ №{order.number} принят в обработку.\n'
                f'Адрес доставки: {order.contact.full_address}\n'
                f'Итого: {order.total_amount} руб.\n\n'
                f'Состав заказа:\n{items_text}\n\n'
                f'Спасибо за покупку!'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.contact.email],
            fail_silently=False,
        )


class OrderListView(APIView):
    """Список (история) заказов текущего пользователя."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        orders = Order.objects.filter(user=request.user)
        serializer = OrderListSerializer(orders, many=True)
        return Response(serializer.data)


class OrderDetailView(APIView):
    """Детали конкретного заказа (только свои)."""

    permission_classes = (IsAuthenticated,)

    def get(self, request, pk):
        try:
            order = Order.objects.prefetch_related('items').get(
                pk=pk, user=request.user
            )
        except Order.DoesNotExist:
            return Response(
                {'detail': 'Заказ не найден'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = OrderSerializer(order)
        return Response(serializer.data)