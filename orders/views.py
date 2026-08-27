"""API-вьюхи приложения orders: корзина, контакты, заказы."""
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.tasks import send_email

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
    """Корзина текущего пользователя."""

    permission_classes = (IsAuthenticated,)

    def get_cart(self, user):
        cart, _ = Cart.objects.get_or_create(user=user)
        return cart

    def get(self, request):
        cart = self.get_cart(request.user)
        return Response(CartSerializer(cart).data)

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
    """Конкретная позиция корзины (PUT/DELETE)."""

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
    """Контакты (адреса доставки) текущего пользователя."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        contacts = Contact.objects.filter(user=request.user)
        return Response(ContactSerializer(contacts, many=True).data)

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ContactDeleteView(APIView):
    """Удаление контакта (адреса доставки)."""

    permission_classes = (IsAuthenticated,)

    def delete(self, request, pk):
        try:
            contact = Contact.objects.get(pk=pk, user=request.user)
        except Contact.DoesNotExist:
            return Response(
                {'detail': 'Контакт не найден или не принадлежит вам'},
                status=status.HTTP_404_NOT_FOUND,
            )
        contact.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==================== ЗАКАЗЫ ====================


class OrderConfirmView(APIView):
    """
    Подтверждение заказа (ключевой сценарий ТЗ).
    Письма клиенту и админу отправляются через Celery.
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = OrderConfirmSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        basket = serializer.validated_data['basket_obj']
        contact = serializer.validated_data['contact_obj']

        with transaction.atomic():
            total = basket.total_amount
            order = Order.objects.create(
                user=request.user,
                contact=contact,
                total_amount=total,
            )

            for cart_item in basket.items.select_related('product'):
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    product_name=cart_item.product.name,
                    price=cart_item.product.price,
                    quantity=cart_item.quantity,
                )
                product = cart_item.product
                product.quantity = max(0, product.quantity - cart_item.quantity)
                product.save(update_fields=['quantity'])

            basket.items.all().delete()

        # Письма через Celery (не блокируют HTTP-ответ)
        self._send_confirmation_email(order)
        self._send_admin_invoice(order)

        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _build_items_text(order) -> str:
        items_lines = []
        for item in order.items.all():
            items_lines.append(
                f'  • {item.product_name} × {item.quantity} = {item.amount} руб.'
            )
        return '\n'.join(items_lines) if items_lines else '(пусто)'

    @staticmethod
    def _send_confirmation_email(order: Order) -> None:
        items_text = OrderConfirmView._build_items_text(order)
        send_email.delay(
            subject=f'Заказ №{order.number} подтверждён',
            message=(
                f'Здравствуйте, {order.user.first_name}!\n\n'
                f'Ваш заказ №{order.number} принят в обработку.\n'
                f'Адрес доставки: {order.contact.full_address}\n'
                f'Итого: {order.total_amount} руб.\n\n'
                f'Состав заказа:\n{items_text}\n\n'
                f'Спасибо за покупку!'
            ),
            recipient_list=[order.contact.email],
        )

    @staticmethod
    def _send_admin_invoice(order: Order) -> None:
        items_lines = []
        for item in order.items.all():
            items_lines.append(
                f'  • {item.product_name} × {item.quantity} '
                f'× {item.price} руб. = {item.amount} руб.'
            )
        items_text = '\n'.join(items_lines) if items_lines else '(пусто)'

        send_email.delay(
            subject=f'Новый заказ №{order.number}',
            message=(
                f'Поступил новый заказ!\n\n'
                f'Номер: {order.number}\n'
                f'Клиент: {order.user.first_name} {order.user.last_name} ({order.user.email})\n'
                f'Адрес доставки: {order.contact.full_address}\n'
                f'Телефон: {order.contact.phone}\n'
                f'Итого: {order.total_amount} руб.\n\n'
                f'Состав заказа:\n{items_text}'
            ),
            recipient_list=[settings.ADMIN_EMAIL],
        )


class OrderListView(APIView):
    """Список (история) заказов текущего пользователя."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        orders = Order.objects.filter(user=request.user)
        return Response(OrderListSerializer(orders, many=True).data)


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
        return Response(OrderSerializer(order).data)


class OrderStatusUpdateView(APIView):
    """Редактирование статуса заказа (только админ). Уведомление через Celery."""

    permission_classes = (IsAdminUser,)

    def patch(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(
                {'detail': 'Заказ не найден'},
                status=status.HTTP_404_NOT_FOUND,
            )

        new_status = request.data.get('status')
        if new_status not in [choice[0] for choice in Order.Status.choices]:
            return Response(
                {'detail': 'Недопустимый статус'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = new_status
        order.save(update_fields=['status'])

        send_email.delay(
            subject=f'Статус заказа №{order.number} изменён',
            message=(
                f'Здравствуйте, {order.user.first_name}!\n\n'
                f'Статус вашего заказа №{order.number} изменён на: '
                f'{order.get_status_display()}.\n\n'
                f'Итого: {order.total_amount} руб.'
            ),
            recipient_list=[order.user.email],
        )

        return Response({'number': order.number, 'status': order.get_status_display()})