"""API-вьюхи приложения orders: корзина, контакты, заказы."""
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
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


class ContactDeleteView(APIView):
    """
    Удаление контакта (адреса доставки).

    DELETE — удалить контакт, если он принадлежит пользователю.
    """

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

    Принимает basket_id + contact_id:
    1. Создаёт заказ (Order) со снапшотом цен и названий товаров
    2. Списывает товары со склада
    3. Очищает корзину
    4. Отправляет email-подтверждение клиенту
    5. Отправляет накладную администратору (критерий ТЗ)
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

        # 4. Отправляем email клиенту (пока в консоль, позже — Celery)
        self._send_confirmation_email(order)

        # 5. Отправляем накладную администратору (критерий ТЗ)
        self._send_admin_invoice(order)

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
            fail_silently=True,
        )

    @staticmethod
    def _send_admin_invoice(order: Order) -> None:
        """Отправляет накладную администратору (критерий ТЗ)."""
        items_lines = []
        for item in order.items.all():
            items_lines.append(
                f'  • {item.product_name} × {item.quantity} '
                f'× {item.price} руб. = {item.amount} руб.'
            )
        items_text = '\n'.join(items_lines) if items_lines else '(пусто)'

        send_mail(
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
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=True,
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


class OrderStatusUpdateView(APIView):
    """
    Редактирование статуса заказа (доступно только администратору).

    PATCH — изменить статус заказа (new, processing, shipped, completed, cancelled).
    """

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
                {'detail': f'Недопустимый статус. Допустимые: {[c[0] for c in Order.Status.choices]}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = new_status
        order.save(update_fields=['status'])

        # Отправляем уведомление клиенту об изменении статуса
        send_mail(
            subject=f'Статус заказа №{order.number} изменён',
            message=(
                f'Здравствуйте, {order.user.first_name}!\n\n'
                f'Статус вашего заказа №{order.number} изменён на: '
                f'{order.get_status_display()}.\n\n'
                f'Итого: {order.total_amount} руб.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=True,
        )

        return Response({'number': order.number, 'status': order.get_status_display()})