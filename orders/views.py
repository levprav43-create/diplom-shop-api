"""API-вьюхи приложения orders: корзина и её позиции."""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Cart, CartItem
from .serializers import (
    CartItemCreateSerializer,
    CartItemSerializer,
    CartItemUpdateSerializer,
    CartSerializer,
)


class CartView(APIView):
    """
    Корзина текущего пользователя.

    GET  — получить содержимое корзины.
    POST — добавить товар (если уже есть — увеличить количество).
    """

    permission_classes = (IsAuthenticated,)

    def get_cart(self, user):
        """Получить или создать корзину пользователя."""
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
        """Найти позицию корзины текущего пользователя."""
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