"""API-вьюхи приложения users: регистрация и вход."""
from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginSerializer, RegisterSerializer

User = get_user_model()


class RegisterView(APIView):
    """Регистрация нового клиента (доступна без входа)."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # Сразу выдаём токен, чтобы клиент мог работать с API
        token = Token.objects.create(user=user)
        return Response(
            {'id': user.id, 'email': user.email, 'token': token.key},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Вход по email и паролю; возвращает токен для дальнейших запросов."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
        )
        if user is None:
            return Response(
                {'detail': 'Неверный email или пароль'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'email': user.email, 'token': token.key})